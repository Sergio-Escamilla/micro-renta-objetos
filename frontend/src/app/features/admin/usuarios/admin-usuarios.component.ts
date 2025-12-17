import { Component, OnInit } from '@angular/core';
import { AdminService, AdminUsuario, Paginated } from 'src/app/core/services/admin.service';

@Component({
	selector: 'app-admin-usuarios',
	templateUrl: './admin-usuarios.component.html',
	styleUrls: ['./admin-usuarios.component.scss'],
})
export class AdminUsuariosComponent implements OnInit {
	loading = false;
	errorMessage = '';

	search = '';
	page = 1;
	perPage = 10;

	data: Paginated<AdminUsuario> | null = null;

	constructor(private readonly adminService: AdminService) {}

	ngOnInit(): void {
		this.cargar();
	}

	buscar(): void {
		this.page = 1;
		this.cargar();
	}

	private cargar(): void {
		this.loading = true;
		this.errorMessage = '';

		this.adminService
			.getUsuarios({ search: this.search?.trim() || undefined, page: this.page, per_page: this.perPage })
			.subscribe({
				next: (resp) => {
					this.data = resp;
					this.loading = false;
				},
				error: (err) => {
					this.loading = false;
					this.errorMessage = err?.error?.message || 'No se pudieron cargar los usuarios.';
				},
			});
	}
}
