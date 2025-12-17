// src/app/core/services/auth.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';

interface ApiResponse<T> {
  success: boolean;
  message: string;
  data?: T;
}

type LoginData = {
  access_token: string;
  refresh_token?: string;
  usuario?: any;
};

type MeData = {
  id: number;
  nombre: string;
  apellidos: string;
  correo_electronico: string;
  telefono?: string | null;
  ciudad?: string | null;
  estado?: string | null;
  pais?: string | null;
  direccion_completa?: string | null;
  foto_perfil?: string | null;
  roles?: string[];
  verificado?: boolean;
  email_verificado?: boolean;
};

type RegisterPayload = {
  nombre: string;
  apellidos: string;
  correo_electronico: string;
  contrasena: string;
};

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly TOKEN_KEY = 'mr_token';
  private readonly ACCESS_TOKEN_KEY = 'access_token';

  constructor(private http: HttpClient, private router: Router) {}

  register(payload: RegisterPayload): Observable<ApiResponse<any>> {
    const url = `${environment.apiUrl}/auth/register`;
    return this.http.post<ApiResponse<any>>(url, payload);
  }

  login(correo_electronico: string, contrasena: string): Observable<ApiResponse<LoginData>> {
    const url = `${environment.apiUrl}/auth/login`;
    const body = { correo_electronico, contrasena };

    return this.http.post<ApiResponse<LoginData>>(url, body).pipe(
      tap((resp) => {
        if (resp.success && resp.data?.access_token) {
          localStorage.setItem(this.TOKEN_KEY, resp.data.access_token);
          // Compatibilidad: algunas pantallas esperan esta key
          localStorage.setItem(this.ACCESS_TOKEN_KEY, resp.data.access_token);
          // aquí podrías guardar el usuario también si quieres
        }
      })
    );
  }

  me(): Observable<ApiResponse<MeData>> {
    const url = `${environment.apiUrl}/auth/me`;
    return this.http.get<ApiResponse<MeData>>(url);
  }

  enviarVerificacionEmail(): Observable<ApiResponse<any>> {
    const url = `${environment.apiUrl}/auth/enviar-verificacion`;
    return this.http.post<ApiResponse<any>>(url, {});
  }

  verificarEmail(token: string): Observable<ApiResponse<any>> {
    const url = `${environment.apiUrl}/auth/verificar?token=${encodeURIComponent(token)}`;
    return this.http.get<ApiResponse<any>>(url);
  }

  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.ACCESS_TOKEN_KEY);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return (
      localStorage.getItem(this.TOKEN_KEY) ||
      localStorage.getItem(this.ACCESS_TOKEN_KEY)
    );
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  getUserId(): number | null {
    const token = this.getToken();
    if (!token) return null;

    const parts = token.split('.');
    if (parts.length < 2) return null;

    try {
      const base64Url = parts[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
      const json = decodeURIComponent(
        atob(padded)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      const payload = JSON.parse(json);
      const sub = payload?.sub;
      const id = Number(sub);
      return Number.isFinite(id) ? id : null;
    } catch {
      return null;
    }
  }

  getRoles(): string[] {
    const token = this.getToken();
    if (!token) return [];

    const parts = token.split('.');
    if (parts.length < 2) return [];

    try {
      const base64Url = parts[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
      const json = decodeURIComponent(
        atob(padded)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      const payload = JSON.parse(json);
      const roles = payload?.roles;
      return Array.isArray(roles) ? roles.map((r) => String(r)) : [];
    } catch {
      return [];
    }
  }
}
