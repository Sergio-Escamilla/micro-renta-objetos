import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AdminIncidente, AdminService, Paginated } from 'src/app/core/services/admin.service';
import { RentaService } from 'src/app/core/services/renta.service';

type ResolverFormState = {
	open: boolean;
	decision: 'liberar' | 'retener_parcial' | 'retener_total';
	monto_retenido: number | null;
	nota: string;
	loading: boolean;
	error: string;
};

@Component({
	selector: 'app-admin-incidentes',
	templateUrl: './admin-incidentes.component.html',
	styleUrls: ['./admin-incidentes.component.scss'],
})
export class AdminIncidentesComponent implements OnInit {
	loading = false;
	errorMessage = '';
	successMessage = '';

	estado: 'abierto' | 'resuelto' = 'abierto';
	page = 1;
	perPage = 10;

	data: Paginated<AdminIncidente> | null = null;
	resolverState: Record<number, ResolverFormState> = {};

	constructor(
		private readonly adminService: AdminService,
		private readonly rentaService: RentaService,
		private readonly router: Router
	) {}

	ngOnInit(): void {
		this.cargar();
	}

	formatMoney(v: any): string {
		const n = typeof v === 'string' ? Number(v) : v;
		if (typeof n !== 'number' || !Number.isFinite(n)) return '-';
		return `$${Math.round(n) === n ? n : n.toFixed(2)}`;
	}

	decisionLabel(v: any): string {
		const s = String(v ?? '').trim();
		if (s === 'liberar') return 'Liberar depósito';
		if (s === 'retener_parcial') return 'Retener parcial';
		if (s === 'retener_total') return 'Retener total';
		return s || '-';
	}

	setEstado(est: 'abierto' | 'resuelto'): void {
		if (this.estado === est) return;
		this.estado = est;
		this.page = 1;
		this.cargar();
	}

	verRenta(idRenta: number): void {
		this.router.navigate(['/rentas/resumen', idRenta]);
	}

	toggleResolver(inc: AdminIncidente): void {
		const id = inc.id;
		if (!this.resolverState[id]) {
			this.resolverState[id] = {
				open: true,
				decision: 'liberar',
				monto_retenido: null,
				nota: '',
				loading: false,
				error: '',
			};
			return;
		}
		this.resolverState[id].open = !this.resolverState[id].open;
		this.resolverState[id].error = '';
	}

	resolver(inc: AdminIncidente): void {
		const st = this.resolverState[inc.id];
		if (!st || st.loading) return;

		this.successMessage = '';
		const deposito = typeof inc?.renta?.monto_deposito === 'number' ? inc.renta?.monto_deposito : null;
		if ((st.decision === 'retener_parcial' || st.decision === 'retener_total') && !(st.nota || '').trim()) {
			st.error = 'La nota es obligatoria cuando se retiene el depósito.';
			return;
		}
		if (st.decision === 'retener_parcial') {
			if (st.monto_retenido == null || typeof st.monto_retenido !== 'number' || !Number.isFinite(st.monto_retenido)) {
				st.error = 'Indica un monto retenido válido.';
				return;
			}
			if (deposito != null && !(st.monto_retenido > 0 && st.monto_retenido < deposito)) {
				st.error = 'El monto retenido debe ser mayor a 0 y menor al depósito.';
				return;
			}
		}

		st.loading = true;
		st.error = '';

		const payload: any = {
			decision: st.decision,
			monto_retenido: st.monto_retenido,
			nota: st.nota || null,
		};

		this.rentaService.resolverIncidente(inc.id_renta, payload).subscribe({
			next: () => {
				st.loading = false;
				st.open = false;
				this.successMessage = 'Incidente resuelto.';
				this.cargar();
			},
			error: (err) => {
				st.loading = false;
				st.error = err?.error?.message || 'No se pudo resolver el incidente.';
			},
		});
	}

	private cargar(): void {
		this.loading = true;
		this.errorMessage = '';
		this.successMessage = '';
		this.adminService
			.getIncidentes({ estado: this.estado, page: this.page, per_page: this.perPage })
			.subscribe({
				next: (resp) => {
					this.data = resp;
					this.loading = false;
				},
				error: (err) => {
					this.loading = false;
					this.errorMessage = err?.error?.message || 'No se pudieron cargar los incidentes.';
				},
			});
	}
}
