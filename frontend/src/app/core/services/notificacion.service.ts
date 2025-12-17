import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export type Notificacion = {
  id: number;
  tipo: string;
  mensaje: string;
  leida: boolean;
  created_at: string;
  meta_json?: string | null;
  meta?: any;
};

type ApiResponse<T> = {
  success: boolean;
  data: T;
  message?: string;
};

@Injectable({ providedIn: 'root' })
export class NotificacionService {
  private baseUrl = `${environment.apiUrl}/notificaciones`;

  constructor(private http: HttpClient) {}

  listar(): Observable<{ items: Notificacion[]; unread_count: number }> {
    return this.http
      .get<ApiResponse<{ items: Notificacion[]; unread_count: number }>>(this.baseUrl)
      .pipe(
      map((resp) => {
        const data = resp.data;
        const items = (data?.items ?? []).map((n: any) => {
          const raw = n?.meta_json;
          let meta: any = undefined;
          if (raw) {
            try {
              meta = JSON.parse(String(raw));
            } catch {
              meta = undefined;
            }
          }
          return { ...n, meta_json: raw ?? null, meta } as Notificacion;
        });
        return { ...data, items };
      })
    );
  }

  marcarLeida(id: number): Observable<void> {
    return this.http
      .post<ApiResponse<{ id: number }>>(`${this.baseUrl}/${id}/leer`, {})
      .pipe(map(() => void 0));
  }
}
