import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Conversation, Message

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        
        # Anonymous users can't connect
        if self.user.is_anonymous:
            await self.close()
            return
        
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'chat_{self.conversation_id}'
        
        # Check if the user is part of this conversation
        if not await self.user_in_conversation(self.conversation_id, self.user.id):
            await self.close()
            return
        
        # Join the conversation group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave the conversation group
        if hasattr(self, 'conversation_group_name'):
            await self.channel_layer.group_discard(
                self.conversation_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', 'message')
        
        if message_type == 'message':
            message = data.get('message', '')
            
            # Store the message in the database
            message_instance = await self.save_message(
                conversation_id=self.conversation_id,
                sender_id=self.user.id,
                content=message
            )
            
            # Send message to the conversation group
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_id': self.user.id,
                    'sender_name': f"{self.user.first_name} {self.user.last_name}".strip(),
                    'message_id': message_instance.id,
                    'timestamp': message_instance.created_at.isoformat()
                }
            )
        elif message_type == 'read':
            message_id = data.get('message_id')
            
            if message_id:
                # Mark message as read
                await self.mark_message_read(message_id)
                
                # Send read receipt to the conversation group
                await self.channel_layer.group_send(
                    self.conversation_group_name,
                    {
                        'type': 'read_receipt',
                        'message_id': message_id,
                        'user_id': self.user.id,
                    }
                )
        elif message_type == 'typing':
            is_typing = data.get('is_typing', False)
            
            # Send typing indicator to the conversation group
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'typing_indicator',
                    'user_id': self.user.id,
                    'is_typing': is_typing
                }
            )
    
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'message_id': event['message_id'],
            'timestamp': event['timestamp']
        }))
    
    async def read_receipt(self, event):
        # Send read receipt to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'user_id': event['user_id']
        }))
    
    async def typing_indicator(self, event):
        # Send typing indicator to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'is_typing': event['is_typing']
        }))
    
    @database_sync_to_async
    def user_in_conversation(self, conversation_id, user_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            return conversation.participants.filter(id=user_id).exists()
        except Conversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, conversation_id, sender_id, content):
        conversation = Conversation.objects.get(id=conversation_id)
        sender = User.objects.get(id=sender_id)
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content
        )
        
        # Update conversation timestamp
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])
        
        return message
    
    @database_sync_to_async
    def mark_message_read(self, message_id):
        try:
            message = Message.objects.get(id=message_id)
            
            # Only mark as read if the current user is not the sender
            if message.sender.id != self.user.id:
                message.is_read = True
                message.read_at = timezone.now()
                message.save(update_fields=['is_read', 'read_at'])
        except Message.DoesNotExist:
            pass
