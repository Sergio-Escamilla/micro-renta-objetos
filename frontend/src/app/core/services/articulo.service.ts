
// frontend/src/app/core/services/articulo.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { Articulo } from '../models/articulo.model';
import { environment } from '../../../environments/environment';

interface ListadoArticulosResponse {
  success: boolean;
  data: Articulo[];
}

interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export type CrearArticuloPayload = {
  titulo: string;
  descripcion: string;
  id_categoria: number;
  unidad_precio?: 'por_hora' | 'por_dia' | 'por_semana' | string;
  precio_renta_dia?: number | null;
  precio_renta_hora?: number | null;
  deposito_garantia?: number | null;
  ciudad?: string | null;
  ubicacion_texto?: string | null;
  urls_imagenes?: string[];
};

export type ActualizarArticuloPayload = {
  titulo?: string;
  descripcion?: string;
  unidad_precio?: 'por_hora' | 'por_dia' | 'por_semana' | string | null;
  precio_renta_dia?: number | null;
  precio_renta_hora?: number | null;
  deposito_garantia?: number | null;
  estado_publicacion?: 'publicado' | 'pausado' | string | null;
};

@Injectable({ providedIn: 'root' })
export class ArticuloService {
  private baseUrl = `${environment.apiUrl}/articulos`;

  constructor(private http: HttpClient) {}

  getArticulos(): Observable<Articulo[]> {
    return this.http
      .get<ListadoArticulosResponse>(this.baseUrl)
      .pipe(map((resp) => resp.data ?? []));
  }

  misArticulos(): Observable<Articulo[]> {
    return this.http
      .get<ListadoArticulosResponse>(`${this.baseUrl}/mis`)
      .pipe(map((resp) => resp.data ?? []));
  }

  crearArticulo(payload: CrearArticuloPayload): Observable<Articulo> {
    return this.http
      .post<ApiResponse<Articulo>>(this.baseUrl, payload)
      .pipe(map((resp) => resp.data));
  }

  subirImagenes(articuloId: number, files: File[]): Observable<{ imagenes: string[] }>
  {
    const formData = new FormData();
    for (const f of files) {
      formData.append('imagenes', f);
    }

    return this.http
      .post<ApiResponse<{ articulo_id: number; imagenes: string[] }>>(
        `${this.baseUrl}/${articuloId}/imagenes`,
        formData
      )
      .pipe(map((resp) => resp.data));
  }

  getArticuloPorId(id: number): Observable<Articulo> {
    return this.http
      .get<{ success: boolean; data: Articulo }>(`${this.baseUrl}/${id}`)
      .pipe(map((resp) => resp.data));
  }

	actualizarArticulo(id: number, payload: ActualizarArticuloPayload): Observable<Articulo> {
		return this.http
			.patch<ApiResponse<Articulo>>(`${this.baseUrl}/${id}`, payload)
			.pipe(map((resp) => resp.data));
	}

  eliminarImagen(articuloId: number, imagenId: number): Observable<{ deleted: boolean }> {
    return this.http
      .delete<ApiResponse<{ deleted: boolean }>>(`${this.baseUrl}/${articuloId}/imagenes/${imagenId}`)
      .pipe(map((resp) => resp.data));
  }

  reordenarImagenes(articuloId: number, ordenIds: number[]): Observable<{ ok: boolean }> {
    return this.http
      .patch<ApiResponse<{ ok: boolean }>>(`${this.baseUrl}/${articuloId}/imagenes/orden`, { orden: ordenIds })
      .pipe(map((resp) => resp.data));
  }

  marcarImagenPrincipal(articuloId: number, imagenId: number): Observable<{ ok: boolean }> {
    return this.http
      .patch<ApiResponse<{ ok: boolean }>>(`${this.baseUrl}/${articuloId}/imagenes/${imagenId}/principal`, {})
      .pipe(map((resp) => resp.data));
  }

  getOcupacion(
    idArticulo: number,
    desde: string,
    hasta: string
  ): Observable<Array<{ inicio: string; fin: string }>> {
    const params = new HttpParams().set('desde', desde).set('hasta', hasta);
    return this.http
      .get<{ success: boolean; data: { ocupado: Array<{ inicio: string; fin: string }> } }>(
        `${this.baseUrl}/${idArticulo}/ocupacion`,
        { params }
      )
      .pipe(map((resp) => resp.data?.ocupado ?? []));
  }
}

