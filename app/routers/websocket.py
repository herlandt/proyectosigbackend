import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.models.linea import Linea

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
	"""
	Mantiene las conexiones WebSocket activas agrupadas por linea_id.
	Thread-safe para uso con un solo worker (Uvicorn single-process).
	Para multi-worker se necesitaria Redis pub/sub.
	"""

	def __init__(self):
		self._conexiones: Dict[str, List[WebSocket]] = {}

	async def conectar(self, linea_id: str, websocket: WebSocket):
		await websocket.accept()
		if linea_id not in self._conexiones:
			self._conexiones[linea_id] = []
		self._conexiones[linea_id].append(websocket)

	def desconectar(self, linea_id: str, websocket: WebSocket):
		conexiones = self._conexiones.get(linea_id)
		if not conexiones:
			return
		if websocket in conexiones:
			conexiones.remove(websocket)
		if not conexiones:
			del self._conexiones[linea_id]

	async def broadcast(self, linea_id: str, mensaje: dict):
		"""Envia un mensaje JSON a todos los clientes de una linea."""
		conexiones = list(self._conexiones.get(linea_id, []))
		desconectados: List[WebSocket] = []

		for ws in conexiones:
			try:
				await ws.send_json(mensaje)
			except Exception:
				desconectados.append(ws)

		for ws in desconectados:
			self.desconectar(linea_id, ws)

	def clientes_activos(self, linea_id: str) -> int:
		return len(self._conexiones.get(linea_id, []))


ws_manager = ConnectionManager()


def _linea_existe(linea_id: str) -> bool:
	"""Valida (en una sesion corta) que la linea exista, sin retener la conexion."""
	db = SessionLocal()
	try:
		return db.query(Linea.id).filter(Linea.id == linea_id).first() is not None
	finally:
		db.close()


@router.websocket("/ws/lineas/{linea_id}/posiciones")
async def websocket_posiciones(
	linea_id: str,
	websocket: WebSocket,
	token: Optional[str] = Query(default=None),
):
	# 1. linea_id debe ser un UUID valido y la linea debe existir.
	try:
		uuid.UUID(linea_id)
		valida = _linea_existe(linea_id)
	except ValueError:
		valida = False
	except Exception:
		await websocket.close(code=1011)  # error interno (p.ej. BD no disponible)
		return
	if not valida:
		await websocket.close(code=4404)  # linea inexistente
		return

	# 2. Autenticacion: obligatoria si WS_REQUIRE_AUTH=true; si llega token, debe ser valido.
	#    Por defecto la lectura de posiciones es publica (el pasajero no inicia sesion).
	if settings.WS_REQUIRE_AUTH or token is not None:
		if token is None or decode_access_token(token) is None:
			await websocket.close(code=4401)  # no autorizado
			return

	# 3. Conexion aceptada.
	await ws_manager.conectar(linea_id, websocket)
	try:
		while True:
			await websocket.receive_text()
	except WebSocketDisconnect:
		ws_manager.desconectar(linea_id, websocket)
