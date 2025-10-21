"""
WebSocket Consumers for Real-Time Analysis Progress Updates

This module provides WebSocket consumers for real-time communication
during analysis operations.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer


class AnalysisProgressConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for analysis progress updates.

    Handles real-time progress notifications during analysis operations.
    Clients connect to ws://host/ws/analysis/<session_id>/ to receive updates.
    """

    async def connect(self):
        """
        Handle WebSocket connection.

        Adds the client to the session-specific room group.
        """
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'analysis_{self.session_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'Connected to analysis progress updates',
            'session_id': self.session_id,
        }))

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.

        Removes the client from the room group.
        """
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Handle messages from WebSocket client.

        Currently not used, but can be extended for client-to-server communication.
        """
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'unknown')

            # Echo back for now (can be extended)
            await self.send(text_data=json.dumps({
                'type': 'echo',
                'message': f'Received: {message_type}',
            }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON',
            }))

    # Event handlers for messages sent from channel layer

    async def analysis_progress(self, event):
        """
        Handler for progress update events.

        Receives progress updates from the channel layer and sends them to the client.

        Args:
            event: Dict containing progress information
                - message: Progress message
                - percentage: Progress percentage (0-100)
                - current_step: Current step name
        """
        await self.send(text_data=json.dumps({
            'type': 'progress',
            'message': event['message'],
            'percentage': event.get('percentage', 0),
            'current_step': event.get('current_step', ''),
            'timestamp': event.get('timestamp', ''),
        }))

    async def analysis_complete(self, event):
        """
        Handler for analysis completion events.

        Args:
            event: Dict containing completion information
                - message: Completion message
                - success: Boolean indicating success
                - results_url: URL to view results
        """
        await self.send(text_data=json.dumps({
            'type': 'complete',
            'message': event['message'],
            'success': event.get('success', True),
            'results_url': event.get('results_url', ''),
            'timestamp': event.get('timestamp', ''),
        }))

    async def analysis_error(self, event):
        """
        Handler for analysis error events.

        Args:
            event: Dict containing error information
                - message: Error message
                - error: Error details
        """
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': event['message'],
            'error': event.get('error', ''),
            'timestamp': event.get('timestamp', ''),
        }))

    async def analysis_log(self, event):
        """
        Handler for analysis log events.

        Args:
            event: Dict containing log information
                - message: Log message
                - level: Log level (info, warning, debug)
        """
        await self.send(text_data=json.dumps({
            'type': 'log',
            'message': event['message'],
            'level': event.get('level', 'info'),
            'timestamp': event.get('timestamp', ''),
        }))
