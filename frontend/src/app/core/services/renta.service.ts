import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { environment } from 'src/environments/environment';
import { ModalidadRenta, RentaResumen } from '../models/renta.model';

interface ApiResponse<T> {
	success: boolean;
	data: T;
	message?: string;
}

type MisRentasResponse = {
	items: RentaResumen[];
	como: string;
};

type ChatMessage = {
	id: number;
	id_renta: number;
	id_emisor: number;
	mensaje: string;
	created_at?: string | null;
};

type ChatResponse = {
	items: ChatMessage[];
};

type MisRentasInboxItem = {
	id_renta: number;
	estado: string;
	entrega_modo?: string | null;
	punto_entrega_nombre?: string | null;
	fechas?: { inicio?: string | null; fin?: string | null } | null;
	modalidad?: string | null;
	total?: number | null;
	deposito?: number | null;
	monto_deposito?: number | null;
	deposito_liberado?: boolean;
	reembolso_simulado?: boolean;
	timeline?: { [k: string]: string | null };
	fecha_pago?: string | null;
	fecha_coordinacion_confirmada?: string | null;
	fecha_entrega?: string | null;
	fecha_entrega_confirmada?: string | null;
	fecha_en_uso?: string | null;
	fecha_devolucion?: string | null;
	fecha_finalizacion?: string | null;
	fecha_incidente?: string | null;
	fecha_cancelacion?: string | null;
	fecha_expiracion?: string | null;
	fecha_liberacion_deposito?: string | null;
	articulo?: { id_articulo: number; titulo?: string | null; imagen?: string | null } | null;
};

type MisRentasInboxResponse = {
	items: MisRentasInboxItem[];
	page: number;
	per_page: number;
	total: number;
};

export type CrearRentaPayload = {
	id_articulo: number;
	fecha_inicio: string;
	fecha_fin: string;
	modalidad: ModalidadRenta;
};

@Injectable({ providedIn: 'root' })
export class RentaService {
	private baseUrl = `${environment.apiUrl}/rentas`;

	constructor(private http: HttpClient) {}

	crearRenta(payload: CrearRentaPayload): Observable<RentaResumen> {
		return this.http
			.post<ApiResponse<RentaResumen>>(this.baseUrl, payload)
			.pipe(map((resp) => resp.data));
	}

	obtenerRenta(idRenta: number): Observable<RentaResumen> {
		return this.http
			.get<ApiResponse<RentaResumen>>(`${this.baseUrl}/${idRenta}`)
			.pipe(map((resp) => resp.data));
	}

	pagarRenta(idRenta: number): Observable<RentaResumen> {
		return this.http
			.post<ApiResponse<RentaResumen>>(`${this.baseUrl}/${idRenta}/pagar`, {})
			.pipe(map((resp) => resp.data));
	}

	confirmar(idRenta: number): Observable<RentaResumen> {
		return this.http
			.post<ApiResponse<RentaResumen>>(`${this.baseUrl}/${idRenta}/confirmar`, {})
			.pipe(map((resp) => resp.data));
	}

	enUso(idRenta: number): Observable<RentaResumen> {
		return this.http
			.post<ApiResponse<RentaResumen>>(`${this.baseUrl}/${idRenta}/en-uso`, {})
			.pipe(map((resp) => resp.data));
	}

	devolver(idRenta: number): Observable<RentaResumen> {
		return this.http
			.post<ApiResponse<RentaResumen>>(`${this.baseUrl}/${idRenta}/devolver`, {})
			.pipe(map((resp) => resp.data));
	}

	finalizar(idRenta: number): Observable<RentaResumen> {
		return this.http
			.post<ApiResponse<RentaResumen>>(`${this.baseUrl}/${idRenta}/finalizar`, {})
			.pipe(map((resp) => resp.data));
	}

	cancelar(idRenta: number, motivo?: string | null): Observable<RentaResumen> {
		return this.http
			.post<ApiResponse<RentaResumen>>(`${this.baseUrl}/${idRenta}/cancelar`, { motivo: motivo ?? null })
			.pipe(map((resp) => resp.data));
	}

	incidente(idRenta: number, descripcion: string): Observable<RentaResumen> {
		return this.http
			.post<ApiResponse<RentaResumen>>(`${this.baseUrl}/${idRenta}/incidente`, { descripcion })
			.pipe(map((resp) => resp.data));
	}

	resolverIncidente(
		idRenta: number,
		payload: {
			decision: 'liberar' | 'retener_parcial' | 'retener_total';
			monto_retenido?: number | null;
			nota?: string | null;
		}
	): Observable<RentaResumen> {
		return this.http
			.post<ApiResponse<RentaResumen>>(`${this.baseUrl}/${idRenta}/resolver-incidente`, payload)
			.pipe(map((resp) => resp.data));
	}

	obtenerCalificacion(idRenta: number): Observable<any> {
		return this.http
			.get<ApiResponse<any>>(`${this.baseUrl}/${idRenta}/calificacion`)
			.pipe(map((resp) => resp.data));
	}

	calificar(idRenta: number, payload: { estrellas: number; comentario?: string | null }): Observable<any> {
		return this.http
			.post<ApiResponse<any>>(`${this.baseUrl}/${idRenta}/calificar`, payload)
			.pipe(map((resp) => resp.data));
	}

	listarMisRentas(como: 'arrendatario' | 'propietario' = 'arrendatario'): Observable<RentaResumen[]> {
		return this.http
			.get<ApiResponse<MisRentasResponse>>(`${this.baseUrl}/mis?como=${como}`)
			.pipe(map((resp) => resp.data?.items ?? []));
	}

	misRentas(
		rol: 'dueno' | 'arrendatario',
		estado: 'activas' | 'historial',
		page: number = 1,
		perPage: number = 20
	): Observable<MisRentasInboxResponse> {
		return this.http
			.get<ApiResponse<MisRentasInboxResponse>>(
				`${this.baseUrl}/mias?rol=${rol}&estado=${estado}&page=${page}&per_page=${perPage}`
			)
			.pipe(map((resp) => resp.data));
	}

	chatUnreadCount(idRenta: number): Observable<number> {
		return this.http
			.get<ApiResponse<{ unread: number }>>(`${this.baseUrl}/${idRenta}/chat/unread-count`)
			.pipe(map((resp) => Number(resp.data?.unread ?? 0) || 0));
	}

	chatMarcarLeido(idRenta: number): Observable<void> {
		return this.http
			.post<ApiResponse<any>>(`${this.baseUrl}/${idRenta}/chat/marcar-leido`, {})
			.pipe(map(() => void 0));
	}

	chatUnreadTotal(): Observable<number> {
		return this.http
			.get<ApiResponse<{ total: number }>>(`${this.baseUrl}/chat/unread-total`)
			.pipe(map((resp) => Number(resp.data?.total ?? 0) || 0));
	}

	descargarRecibo(idRenta: number): Observable<Blob> {
		return this.http.get(`${this.baseUrl}/${idRenta}/recibo`, {
			responseType: 'blob',
		});
	}

	coordinar(
		idRenta: number,
		payload: {
			modo_entrega?: 'arrendador' | 'neutral' | string | null;
			entrega_modo?: 'domicilio' | 'punto_entrega' | string | null;
			id_punto_entrega?: number | null;
			zona_publica?: string | null;
			direccion_entrega?: string | null;
			ventanas_entrega_propuestas?: string[] | null;
			ventanas_devolucion_propuestas?: string[] | null;
			confirmar?: boolean;
		}
	): Observable<RentaResumen> {
		return this.http
			.post<ApiResponse<RentaResumen>>(`${this.baseUrl}/${idRenta}/coordinar`, payload)
			.pipe(map((resp) => resp.data));
	}

	aceptarCoordinacion(
		idRenta: number,
		payload: { ventana_entrega: string; ventana_devolucion: string }
	): Observable<RentaResumen> {
		return this.http
			.post<ApiResponse<RentaResumen>>(`${this.baseUrl}/${idRenta}/aceptar-coordinacion`, payload)
			.pipe(map((resp) => resp.data));
	}

	confirmarEntregaOtp(
		idRenta: number,
		payload: { codigo: string; checklist?: string | null }
	): Observable<RentaResumen> {
		return this.http
			.post<ApiResponse<RentaResumen>>(`${this.baseUrl}/${idRenta}/confirmar-entrega-otp`, payload)
			.pipe(map((resp) => resp.data));
	}

	confirmarDevolucionOtp(
		idRenta: number,
		payload: { codigo: string; checklist?: string | null }
	): Observable<RentaResumen> {
		return this.http
			.post<ApiResponse<RentaResumen>>(`${this.baseUrl}/${idRenta}/confirmar-devolucion-otp`, payload)
			.pipe(map((resp) => resp.data));
	}

	getChat(idRenta: number): Observable<ChatMessage[]> {
		return this.http
			.get<ApiResponse<ChatResponse>>(`${this.baseUrl}/${idRenta}/chat`)
			.pipe(map((resp) => resp.data?.items ?? []));
	}

	sendChatMessage(idRenta: number, mensaje: string): Observable<ChatMessage> {
		return this.http
			.post<ApiResponse<ChatMessage>>(`${this.baseUrl}/${idRenta}/chat`, { mensaje })
			.pipe(map((resp) => resp.data));
	}
}

