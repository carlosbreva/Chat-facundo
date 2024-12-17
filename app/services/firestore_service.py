from __future__ import annotations
from firebase_admin import firestore, credentials
from typing import TYPE_CHECKING, List, Optional
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    BaseMessage,
    messages_from_dict,
    messages_to_dict,
)
import firebase_admin
import logging, os


if TYPE_CHECKING:
    from google.cloud.firestore import Client, DocumentReference


logger = logging.getLogger(__name__)
cred = credentials.Certificate("firestore_key.json")
try:
    firebase_admin.initialize_app(cred)
except:
    pass
db = firestore.client()
collection_name = os.getenv('FIRESTORE_COLLECTION_NAME')


def get_or_create_conversation(phone_number):
    doc_ref = db.collection('user_conversations').document(phone_number)

    # Verificar si el documento ya existe
    doc = doc_ref.get()
    if doc.exists:
        return doc_ref
    else:
        # Crear un nuevo documento si no existe
        new_conversation = {'conversations': []}
        doc_ref.set(new_conversation)
        return doc_ref


def add_message_to_conversation(phone_number, message_dict):
    """
    Añade o actualiza un mensaje en la conversación en Firestore.

    Args:
    phone_number (str): Número de teléfono del usuario.
    message_dict (dict): Diccionario con los detalles del mensaje.
    """
    # Referencia al documento de la conversación basado en el número de teléfono
    conversation_ref = db.collection('zensitec').document(phone_number+'_detailed')

    # Verifica si el documento existe
    doc = conversation_ref.get()
    if not doc.exists:
        # Si el documento no existe, crea uno nuevo con el mensaje inicial
        conversation_ref.set({'conversations': [message_dict]})
    else:
        # Si el documento existe, actualiza el array de conversaciones
        conversation_ref.update({
            'conversations': firestore.ArrayUnion([message_dict])
        })


def _get_firestore_client() -> Client:
    try:
        import firebase_admin
        from firebase_admin import firestore
    except ImportError:
        raise ImportError(
            "Could not import firebase-admin python package. "
            "Please install it with `pip install firebase-admin`."
        )

    # For multiple instances, only initialize the app once.
    try:
        firebase_admin.get_app()
    except ValueError as e:
        logger.debug("Initializing Firebase app: %s", e)
        firebase_admin.initialize_app()

    return firestore.client()


class FirestoreChatMessageHistory(BaseChatMessageHistory):
    """Chat message history backed by Google Firestore."""

    def __init__(
        self,
        collection_name: str,
        session_id: str,
        user_id: str,
        firestore_client: Optional[Client] = None,
    ):
        """
        Initialize a new instance of the FirestoreChatMessageHistory class.

        :param collection_name: The name of the collection to use.
        :param session_id: The session ID for the chat..
        :param user_id: The user ID for the chat.
        """
        self.collection_name = collection_name
        self.session_id = session_id
        self.user_id = user_id
        self._document: Optional[DocumentReference] = None
        self.messages: List[BaseMessage] = []
        self.firestore_client = firestore_client or _get_firestore_client()
        self.prepare_firestore()

    def prepare_firestore(self) -> None:
        """Prepare the Firestore client.

        Use this function to make sure your database is ready.
        """
        self._document = self.firestore_client.collection(
            self.collection_name
        ).document(self.session_id)
        self.load_messages()

    def load_messages(self) -> None:
        """Retrieve the messages from Firestore"""
        if not self._document:
            raise ValueError("Document not initialized")
        doc = self._document.get()
        if doc.exists:
            data = doc.to_dict()
            if "messages" in data and len(data["messages"]) > 0:
                self.messages = messages_from_dict(data["messages"])[-10:]

    def add_message(self, message: BaseMessage) -> None:
        self.messages.append(message)
        self.upsert_messages()

    def upsert_messages(self, new_message: Optional[BaseMessage] = None) -> None:
        """Update the Firestore document."""
        if not self._document:
            raise ValueError("Document not initialized")
        self._document.set(
            {
                "id": self.session_id,
                "user_id": self.user_id,
                "messages": messages_to_dict(self.messages),
            }
        )

    def clear(self) -> None:
        """Clear session memory from this memory and Firestore."""
        self.messages = []
        if self._document:
            self._document.delete()