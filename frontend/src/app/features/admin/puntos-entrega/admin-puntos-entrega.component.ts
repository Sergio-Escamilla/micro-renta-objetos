import { Component, OnInit } from '@angular/core';
import { AdminPuntoEntrega, AdminService, Paginated } from 'src/app/core/services/admin.service';

@Component({
	selector: 'app-admin-puntos-entrega',
	templateUrl: './admin-puntos-entrega.component.html',	
	styleUrls: ['./admin-puntos-entrega.component.scss'],
})
export class AdminPuntosEntregaComponent implements OnInit {
	data: Paginated<AdminPuntoEntrega> | null = null;
	loading = false;
	errorMessage = '';

	search = '';
	page = 1;
	per_page = 10;

	editing: AdminPuntoEntrega | null = null;
	nombre = '';
	direccion = '';
	activo = true;

	constructor(private readonly adminService: AdminService) {}

	ngOnInit(): void {
		this.cargar();
	}

	buscar(): void {
		this.page = 1;
		this.cargar();
	}

	cargar(): void {
		this.loading = true;
		this.errorMessage = '';
		this.adminService
			.getPuntosEntrega({ search: this.search?.trim() || undefined, page: this.page, per_page: this.per_page })
			.subscribe({
				next: (data) => {
					this.data = data;
					this.loading = false;
				},
				error: (err) => {
					this.loading = false;
					this.errorMessage = err?.error?.message || 'No se pudieron cargar los puntos de entrega.';
				},
			});
	}

	nuevo(): void {
		this.editing = null;
		this.nombre = '';
		this.direccion = '';
		this.activo = true;
	}

	editar(p: AdminPuntoEntrega): void {
		this.editing = { ...p };
		this.nombre = p.nombre || '';
		this.direccion = (p.direccion || '') as string;
		this.activo = !!p.activo;
	}

	cancelarEdicion(): void {
		this.nuevo();
	}

	guardar(): void {
		const nombre = (this.nombre || '').trim();
		const direccion = (this.direccion || '').trim();
		if (!nombre) {
			this.errorMessage = 'El nombre es obligatorio.';
			return;
		}

		this.loading = true;
		this.errorMessage = '';

		if (this.editing) {
			this.adminService
				.updatePuntoEntrega(this.editing.id, { nombre, direccion: direccion || null, activo: this.activo })
				.subscribe({
					next: () => {
						this.loading = false;
						this.nuevo();
						this.cargar();
					},
					error: (err) => {
						this.loading = false;
						this.errorMessage = err?.error?.message || 'No se pudo actualizar.';
					},
				});
			return;
		}

		this.adminService
			.createPuntoEntrega({ nombre, direccion: direccion || null, activo: this.activo })
			.subscribe({
				next: () => {
					this.loading = false;
					this.nuevo();
					this.cargar();
				},
				error: (err) => {
					this.loading = false;
					this.errorMessage = err?.error?.message || 'No se pudo crear.';
				},
			});
	}

	desactivar(p: AdminPuntoEntrega): void {
		this.loading = true;
		this.errorMessage = '';
		this.adminService.desactivarPuntoEntrega(p.id).subscribe({
			next: () => {
				this.loading = false;
				this.cargar();
			},
			error: (err) => {
				this.loading = false;
				this.errorMessage = err?.error?.message || 'No se pudo desactivar.';
			},
		});
	}
}
