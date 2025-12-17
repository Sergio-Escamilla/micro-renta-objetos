import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { environment } from 'src/environments/environment';

interface ApiResponse<T> {
	success: boolean;
	data: T;
	message?: string;
}

export type UsuarioRatingResumen = {
	id_usuario: number;
	promedio: number;
	total: number;
};

export type UsuarioResumenMe = {
	articulos_publicados: number;
	rentas_como_arrendatario: number;
	rentas_como_propietario: number;
	rating?: UsuarioRatingResumen | null;
};

export type UsuarioMeUpdatePayload = {
	nombre?: string | null;
	apellidos?: string | null;
	telefono?: string | null;
	ciudad?: string | null;
	estado?: string | null;
	pais?: string | null;
	direccion_completa?: string | null;
	foto_perfil?: string | null;
};

@Injectable({ providedIn: 'root' })
export class UsuarioService {
	private baseUrl = `${environment.apiUrl}/usuarios`;

	constructor(private http: HttpClient) {}

	obtenerRating(idUsuario: number): Observable<UsuarioRatingResumen> {
		return this.http
			.get<ApiResponse<UsuarioRatingResumen>>(`${this.baseUrl}/${idUsuario}/rating`)
			.pipe(map((resp) => resp.data));
	}

	resumenMe(): Observable<UsuarioResumenMe> {
		return this.http
			.get<ApiResponse<UsuarioResumenMe>>(`${this.baseUrl}/me/resumen`)
			.pipe(map((resp) => resp.data));
	}

	actualizarMe(payload: UsuarioMeUpdatePayload): Observable<any> {
		return this.http
			.patch<ApiResponse<any>>(`${this.baseUrl}/me`, payload)
			.pipe(map((resp) => resp.data));
	}
}
