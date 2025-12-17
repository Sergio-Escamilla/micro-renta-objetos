import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { environment } from 'src/environments/environment';

type ApiResponse<T> = {
	success: boolean;
	message?: string;
	data: T;
};

export type AdminResumen = {
	usuarios: number;
	articulos: number;
	rentas_activas: number;
	rentas_finalizadas: number;
	incidentes_abiertos: number;
	notificaciones_no_leidas_total?: number | null;
};

export type Paginated<T> = {
	page: number;
	per_page: number;
	total: number;
	items: T[];
};

export type AdminIncidente = {
	id: number;
	id_renta: number;
	estado: 'abierto' | 'resuelto' | string;
	descripcion: string;
	decision?: string | null;
	monto_retenido?: number | null;
	nota?: string | null;
	created_at?: string | null;
	resolved_at?: string | null;
	renta?: {
		id: number;
		estado_renta: string;
		fecha_inicio?: string | null;
		fecha_fin?: string | null;
		precio_total_renta?: number | null;
		monto_deposito?: number | null;
		deposito_liberado?: boolean;
		fecha_liberacion_deposito?: string | null;
	} | null;
	articulo?: { id_articulo: number; titulo: string } | null;
	arrendatario?: { id_usuario: number; nombre: string; apellidos: string } | null;
	propietario?: { id_usuario: number; nombre: string; apellidos: string } | null;
};

export type AdminUsuario = {
	id_usuario: number;
	nombre: string;
	apellidos: string;
	correo_electronico: string;
	estado_cuenta: string;
	roles: string[];
	rentas_count: number;
	rating_promedio: number;
	rating_total: number;
};

export type AdminArticulo = {
	id_articulo: number;
	titulo: string;
	ciudad?: string | null;
	estado_publicacion?: string | null;
	id_propietario: number;
	propietario?: {
		id_usuario: number;
		nombre: string;
		apellidos: string;
		correo_electronico: string;
	} | null;
};

export type AdminPuntoEntrega = {
	id: number;
	nombre: string;
	direccion?: string | null;
	activo: boolean;
	created_at?: string | null;
	updated_at?: string | null;
};

@Injectable({ providedIn: 'root' })
export class AdminService {
	private baseUrl = `${environment.apiUrl}/admin`;

	constructor(private readonly http: HttpClient) {}

	getResumen(): Observable<AdminResumen> {
		return this.http
			.get<ApiResponse<AdminResumen>>(`${this.baseUrl}/resumen`)
			.pipe(map((resp) => resp.data));
	}

	getIncidentes(params: {
		estado?: 'abierto' | 'resuelto' | string;
		page?: number;
		per_page?: number;
	}): Observable<Paginated<AdminIncidente>> {
		const q = new URLSearchParams();
		if (params.estado) q.set('estado', params.estado);
		if (params.page) q.set('page', String(params.page));
		if (params.per_page) q.set('per_page', String(params.per_page));

		const url = `${this.baseUrl}/incidentes${q.toString() ? `?${q.toString()}` : ''}`;
		return this.http
			.get<ApiResponse<Paginated<AdminIncidente>>>(url)
			.pipe(map((resp) => resp.data));
	}

	getUsuarios(params: { search?: string; page?: number; per_page?: number }): Observable<Paginated<AdminUsuario>> {
		const q = new URLSearchParams();
		if (params.search) q.set('search', params.search);
		if (params.page) q.set('page', String(params.page));
		if (params.per_page) q.set('per_page', String(params.per_page));

		const url = `${this.baseUrl}/usuarios${q.toString() ? `?${q.toString()}` : ''}`;
		return this.http
			.get<ApiResponse<Paginated<AdminUsuario>>>(url)
			.pipe(map((resp) => resp.data));
	}

	getArticulos(params: { search?: string; page?: number; per_page?: number }): Observable<Paginated<AdminArticulo>> {
		const q = new URLSearchParams();
		if (params.search) q.set('search', params.search);
		if (params.page) q.set('page', String(params.page));
		if (params.per_page) q.set('per_page', String(params.per_page));

		const url = `${this.baseUrl}/articulos${q.toString() ? `?${q.toString()}` : ''}`;
		return this.http
			.get<ApiResponse<Paginated<AdminArticulo>>>(url)
			.pipe(map((resp) => resp.data));
	}

	setArticuloEstadoPublicacion(idArticulo: number, estado_publicacion: 'publicado' | 'pausado'):
		Observable<{ id_articulo: number; estado_publicacion: string }> {
		return this.http
			.post<ApiResponse<{ id_articulo: number; estado_publicacion: string }>>(
				`${this.baseUrl}/articulos/${idArticulo}/estado-publicacion`,
				{ estado_publicacion }
			)
			.pipe(map((resp) => resp.data));
	}

	getPuntosEntrega(params: { search?: string; page?: number; per_page?: number }): Observable<Paginated<AdminPuntoEntrega>> {
		const q = new URLSearchParams();
		if (params.search) q.set('search', params.search);
		if (params.page) q.set('page', String(params.page));
		if (params.per_page) q.set('per_page', String(params.per_page));

		const url = `${this.baseUrl}/puntos-entrega${q.toString() ? `?${q.toString()}` : ''}`;
		return this.http
			.get<ApiResponse<Paginated<AdminPuntoEntrega>>>(url)
			.pipe(map((resp) => resp.data));
	}

	createPuntoEntrega(payload: { nombre: string; direccion?: string | null; activo?: boolean }): Observable<AdminPuntoEntrega> {
		return this.http
			.post<ApiResponse<AdminPuntoEntrega>>(`${this.baseUrl}/puntos-entrega`, payload)
			.pipe(map((resp) => resp.data));
	}

	updatePuntoEntrega(
		id: number,
		payload: { nombre?: string; direccion?: string | null; activo?: boolean }
	): Observable<AdminPuntoEntrega> {
		return this.http
			.put<ApiResponse<AdminPuntoEntrega>>(`${this.baseUrl}/puntos-entrega/${id}`, payload)
			.pipe(map((resp) => resp.data));
	}

	desactivarPuntoEntrega(id: number): Observable<AdminPuntoEntrega> {
		return this.http
			.delete<ApiResponse<AdminPuntoEntrega>>(`${this.baseUrl}/puntos-entrega/${id}`)
			.pipe(map((resp) => resp.data));
	}
}
