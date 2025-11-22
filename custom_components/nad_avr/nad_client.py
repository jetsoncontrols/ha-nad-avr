"""NAD AVR TCP client with auto-reconnect."""
import asyncio
import logging
from typing import Callable, Optional

_LOGGER = logging.getLogger(__name__)

RECONNECT_DELAY = 5  # seconds
READ_TIMEOUT = 10  # seconds
CONNECT_TIMEOUT = 10  # seconds


class NADClient:
    """NAD AVR TCP client with automatic reconnection."""

    def __init__(self, host: str, port: int, status_callback: Optional[Callable] = None):
        """Initialize the NAD client."""
        self.host = host
        self.port = port
        self._status_callback = status_callback
        self._update_callback: Optional[Callable] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._read_task: Optional[asyncio.Task] = None
        self._should_reconnect = True
        self._lock = asyncio.Lock()
        self._pending_query: Optional[asyncio.Future] = None

    @property
    def connected(self) -> bool:
        """Return if client is connected."""
        return self._connected

    async def connect(self) -> bool:
        """Connect to the NAD AVR."""
        try:
            _LOGGER.debug("Connecting to NAD AVR at %s:%s", self.host, self.port)
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=CONNECT_TIMEOUT
            )
            self._connected = True
            _LOGGER.info("Connected to NAD AVR at %s:%s", self.host, self.port)
            
            # Start reading responses
            if self._read_task is None or self._read_task.done():
                self._read_task = asyncio.create_task(self._read_responses())
            
            if self._status_callback:
                await self._status_callback(True)
            
            return True
        except (asyncio.TimeoutError, OSError, ConnectionRefusedError) as err:
            _LOGGER.error("Failed to connect to NAD AVR: %s", err)
            self._connected = False
            if self._status_callback:
                await self._status_callback(False)
            return False

    async def disconnect(self):
        """Disconnect from the NAD AVR."""
        self._should_reconnect = False
        
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
        
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception as err:
                _LOGGER.debug("Error closing writer: %s", err)
        
        self._connected = False
        self._reader = None
        self._writer = None
        _LOGGER.info("Disconnected from NAD AVR")

    async def _read_responses(self):
        """Read responses from the AVR."""
        try:
            while self._connected and self._reader:
                try:
                    data = await asyncio.wait_for(
                        self._reader.readuntil(b'\n'),
                        timeout=READ_TIMEOUT
                    )
                    if not data:
                        _LOGGER.warning("Connection closed by NAD AVR")
                        break
                    
                    response = data.decode('utf-8', errors='ignore').strip()
                    if response:
                        _LOGGER.debug("Received from NAD: %s", response)
                        
                        # If there's a pending query, resolve it with this response
                        if self._pending_query and not self._pending_query.done():
                            self._pending_query.set_result(response)
                            self._pending_query = None
                        else:
                            # This is an unsolicited update from the device
                            if self._update_callback:
                                try:
                                    await self._update_callback(response)
                                except Exception as err:
                                    _LOGGER.error("Error in update callback: %s", err)
                        
                except asyncio.TimeoutError:
                    # No data received, continue
                    continue
                except Exception as err:
                    _LOGGER.error("Error reading from NAD AVR: %s", err)
                    break
        except Exception as err:
            _LOGGER.error("Error in read loop: %s", err)
        finally:
            await self._handle_disconnect()

    async def _handle_disconnect(self):
        """Handle disconnection and trigger reconnection."""
        if self._connected:
            _LOGGER.warning("Connection to NAD AVR lost")
            self._connected = False
            
            # Cancel any pending queries
            if self._pending_query and not self._pending_query.done():
                self._pending_query.cancel()
            self._pending_query = None
            
            if self._status_callback:
                await self._status_callback(False)
            
            if self._should_reconnect:
                if self._reconnect_task is None or self._reconnect_task.done():
                    self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self):
        """Reconnection loop."""
        while self._should_reconnect and not self._connected:
            _LOGGER.info("Attempting to reconnect to NAD AVR in %s seconds", RECONNECT_DELAY)
            await asyncio.sleep(RECONNECT_DELAY)
            
            if self._should_reconnect:
                await self.connect()

    async def send_command(self, command: str) -> bool:
        """Send a command to the NAD AVR."""
        async with self._lock:
            if not self._connected or not self._writer:
                _LOGGER.warning("Cannot send command, not connected")
                return False
            
            try:
                _LOGGER.debug("Sending command to NAD: %s", command.strip())
                self._writer.write(command.encode('utf-8'))
                await self._writer.drain()
                return True
            except (OSError, ConnectionResetError) as err:
                _LOGGER.error("Error sending command: %s", err)
                await self._handle_disconnect()
                return False

    async def query(self, command: str, timeout: float = 2.0) -> Optional[str]:
        """Send a query command and wait for response."""
        async with self._lock:
            if not self._connected or not self._writer or not self._reader:
                _LOGGER.warning("Cannot query, not connected")
                return None
            
            # Cancel any existing pending query
            if self._pending_query and not self._pending_query.done():
                self._pending_query.cancel()
            
            try:
                _LOGGER.debug("Querying NAD: %s", command.strip())
                
                # Create a future to wait for the response
                self._pending_query = asyncio.get_event_loop().create_future()
                
                # Send the command
                self._writer.write(command.encode('utf-8'))
                await self._writer.drain()
                
                # Wait for the background reader to populate the future
                response = await asyncio.wait_for(
                    self._pending_query,
                    timeout=timeout
                )
                
                _LOGGER.debug("Query response: %s", response)
                return response
                
            except asyncio.TimeoutError:
                _LOGGER.warning("Query timeout: %s", command.strip())
                if self._pending_query and not self._pending_query.done():
                    self._pending_query.cancel()
                self._pending_query = None
                return None
            except asyncio.CancelledError:
                _LOGGER.debug("Query cancelled: %s", command.strip())
                self._pending_query = None
                return None
            except (OSError, ConnectionResetError) as err:
                _LOGGER.error("Error during query: %s", err)
                if self._pending_query and not self._pending_query.done():
                    self._pending_query.cancel()
                self._pending_query = None
                await self._handle_disconnect()
                return None
