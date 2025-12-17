import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AdminArticulo, AdminService, Paginated } from 'src/app/core/services/admin.service';

@Component({
	selector: 'app-admin-articulos',
	templateUrl: './admin-articulos.component.html',
	styleUrls: ['./admin-articulos.component.scss'],
})
export class AdminArticulosComponent implements OnInit {
	loading = false;
	errorMessage = '';

	search = '';
	page = 1;
	perPage = 10;

	data: Paginated<AdminArticulo> | null = null;
	actionLoading: Record<number, boolean> = {};

	constructor(private readonly adminService: AdminService, private readonly router: Router) {}

	ngOnInit(): void {
		this.cargar();
	}

	buscar(): void {
		this.page = 1;
		this.cargar();
	}

	verDetalle(a: AdminArticulo): void {
		this.router.navigate(['/articulos', a.id_articulo]);
	}

	toggleEstado(a: AdminArticulo): void {
		const estado = (a.estado_publicacion || '').toLowerCase();
		if (!estado) return;

		const next = estado === 'pausado' ? 'publicado' : 'pausado';
		this.actionLoading[a.id_articulo] = true;
		this.adminService.setArticuloEstadoPublicacion(a.id_articulo, next as any).subscribe({
			next: (resp) => {
				a.estado_publicacion = resp.estado_publicacion;
				this.actionLoading[a.id_articulo] = false;
			},
			error: (err) => {
				this.actionLoading[a.id_articulo] = false;
				this.errorMessage = err?.error?.message || 'No se pudo actualizar el estado del artículo.';
			},
		});
	}

	private cargar(): void {
		this.loading = true;
		this.errorMessage = '';

		this.adminService
			.getArticulos({ search: this.search?.trim() || undefined, page: this.page, per_page: this.perPage })
			.subscribe({
				next: (resp) => {
					this.data = resp;
					this.loading = false;
				},
				error: (err) => {
					this.loading = false;
					this.errorMessage = err?.error?.message || 'No se pudieron cargar los artículos.';
				},
			});
	}
}
