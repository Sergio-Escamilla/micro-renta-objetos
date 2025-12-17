import { Component, OnInit } from '@angular/core';
import { AdminResumen, AdminService } from 'src/app/core/services/admin.service';

@Component({
	selector: 'app-admin-dashboard',
	templateUrl: './dashboard.component.html',
	styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent implements OnInit {
	loading = false;
	errorMessage = '';

	resumen: AdminResumen | null = null;

	constructor(private readonly adminService: AdminService) {}

	ngOnInit(): void {
		this.cargar();
	}

	private cargar(): void {
		this.loading = true;
		this.errorMessage = '';

		this.adminService.getResumen().subscribe({
			next: (data) => {
				this.resumen = data;
				this.loading = false;
			},
			error: (err) => {
				this.loading = false;
				this.errorMessage = err?.error?.message || 'No se pudo cargar el resumen.';
			},
		});
	}
}
