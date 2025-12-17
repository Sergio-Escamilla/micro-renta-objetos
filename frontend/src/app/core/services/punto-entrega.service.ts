import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { environment } from 'src/environments/environment';

interface ApiResponse<T> {
	success: boolean;
	data: T;
	message?: string;
}

export type PuntoEntregaPublico = {
	id: number;
	nombre: string;
	direccion?: string | null;
	ciudad?: string | null;
	estado?: string | null;
	horario?: string | null;
	notas?: string | null;
};

@Injectable({ providedIn: 'root' })
export class PuntoEntregaService {
	private baseUrl = `${environment.apiUrl}/puntos-entrega`;

	constructor(private http: HttpClient) {}

	listarActivos(): Observable<PuntoEntregaPublico[]> {
		return this.http
			.get<ApiResponse<{ items: PuntoEntregaPublico[] }>>(this.baseUrl)
			.pipe(map((resp) => resp.data?.items ?? []));
	}
}
