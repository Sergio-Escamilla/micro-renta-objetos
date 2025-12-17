// frontend/src/app/features/articulos/listado-articulos/listado-articulos.component.ts
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { ArticuloService } from '../../../core/services/articulo.service';
import { Articulo } from '../../../core/models/articulo.model';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-listado-articulos',
  templateUrl: './listado-articulos.component.html',
  styleUrls: ['./listado-articulos.component.scss'],
})
export class ListadoArticulosComponent implements OnInit {
  articulos: Articulo[] = [];
  loading = false;
  errorMessage = '';

  constructor(
    private articuloService: ArticuloService,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.cargarArticulos();
  }

  cargarArticulos(): void {
    this.loading = true;
    this.errorMessage = '';

    this.articuloService.getArticulos().subscribe({
      next: (arts) => {
        console.log('ARTÍCULOS DESDE API 👉', arts);
        this.articulos = arts;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error cargando artículos', err);
        this.loading = false;
        if (err?.status === 401 || err?.status === 422) {
          this.errorMessage = 'Sesión expirada, inicia sesión.';
          this.authService.logout();
          this.router.navigate(['/login']);
          return;
        }

        this.errorMessage =
          'No se pudieron cargar los artículos. Intenta de nuevo más tarde.';
      },
    });
  }

  irADetalle(art: Articulo): void {
    this.router.navigate(['/articulos', art.id]);
  }

  irAPerfil(): void {
    this.router.navigate(['/perfil']);
  }

  cerrarSesion(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
