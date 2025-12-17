import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Categoria } from '../models/categoria.model';

interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

@Injectable({ providedIn: 'root' })
export class CategoriaService {
  private baseUrl = `${environment.apiUrl}/categorias`;

  constructor(private http: HttpClient) {}

  getCategorias(): Observable<Categoria[]> {
    return this.http
      .get<ApiResponse<Categoria[]>>(this.baseUrl)
      .pipe(map((resp) => resp.data ?? []));
  }
}
