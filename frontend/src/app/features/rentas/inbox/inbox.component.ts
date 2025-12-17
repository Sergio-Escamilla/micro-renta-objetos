import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, finalize, forkJoin, of } from 'rxjs';
import { RentaService } from 'src/app/core/services/renta.service';

type InboxRol = 'dueno' | 'arrendatario';
type InboxEstado = 'activas' | 'historial';

type InboxItem = {
	id_renta: number;
	estado: string;
	entrega_modo?: string | null;
	punto_entrega_nombre?: string | null;
	punto_entrega_direccion?: string | null;
	punto_entrega?: { nombre?: string | null; direccion?: string | null } | null;
	fechas?: { inicio?: string | null; fin?: string | null } | null;
	modalidad?: string | null;
	total?: number | null;
	deposito?: number | null;
	monto_deposito?: number | null;
	deposito_liberado?: boolean;
	reembolso_simulado?: boolean;
	timeline?: { [k: string]: string | null };
	fecha_pago?: string | null;
	fecha_coordinacion_confirmada?: string | null;
	fecha_entrega?: string | null;
	fecha_entrega_confirmada?: string | null;
	fecha_en_uso?: string | null;
	fecha_devolucion?: string | null;
	fecha_finalizacion?: string | null;
	fecha_incidente?: string | null;
	fecha_cancelacion?: string | null;
	fecha_expiracion?: string | null;
	fecha_liberacion_deposito?: string | null;
	articulo?: { id_articulo: number; titulo?: string | null; imagen?: string | null } | null;
};

type MiniStep = {
	key: string;
	label: string;
	done: boolean;
	date?: string | null;
};

type HistStep = {
	key: string;
	label: string;
	date?: string | null;
	status: 'done' | 'pending' | 'alert';
};

type MisRentasInboxResponse = {
	items: InboxItem[];
	page: number;
	per_page: number;
	total: number;
};

type TabKey = 'dueno_activas' | 'arrendatario_activas' | 'historial';

@Component({
	selector: 'app-inbox',
	templateUrl: './inbox.component.html',
	styleUrls: ['./inbox.component.scss'],
})
export class InboxComponent implements OnInit {
	loading = false;
	errorMessage = '';

	selectedTab: TabKey = 'dueno_activas';
	rolHistorial: InboxRol = 'dueno';

	items: InboxItem[] = [];
	unreadByRentaId: Record<number, number> = {};

	constructor(private readonly rentaService: RentaService, private readonly router: Router) {}

	ngOnInit(): void {
		this.cargarTab('dueno_activas');
	}

	cargarTab(tab: TabKey): void {
		this.selectedTab = tab;
		this.errorMessage = '';
		this.items = [];
		this.unreadByRentaId = {};

		let rol: InboxRol = 'dueno';
		let estado: InboxEstado = 'activas';

		if (tab === 'dueno_activas') {
			rol = 'dueno';
			estado = 'activas';
			this.rolHistorial = 'dueno';
		} else if (tab === 'arrendatario_activas') {
			rol = 'arrendatario';
			estado = 'activas';
			this.rolHistorial = 'arrendatario';
		} else {
			rol = this.rolHistorial;
			estado = 'historial';
		}

		this.loading = true;
		this.rentaService
			.misRentas(rol, estado, 1, 20)
			.pipe(
				finalize(() => {
					this.loading = false;
				})
			)
			.subscribe({
				next: (data: MisRentasInboxResponse) => {
					this.items = data?.items ?? [];
					if (estado === 'activas') {
						this.cargarUnreads(this.items);
					}
				},
				error: (err) => {
					this.errorMessage = err?.error?.message || 'No se pudo cargar la bandeja.';
				},
			});
	}

	cambiarRolHistorial(rol: InboxRol): void {
		this.rolHistorial = rol;
		if (this.selectedTab === 'historial') {
			this.cargarTab('historial');
		}
	}

	private cargarUnreads(items: InboxItem[]): void {
		const list = (items ?? []).slice(0, 20);
		if (!list.length) return;

		const calls = list.map((it) =>
			this.rentaService.chatUnreadCount(it.id_renta).pipe(
				catchError(() => of(0))
			)
		);

		forkJoin(calls).subscribe((counts) => {
			const map: Record<number, number> = {};
			for (let i = 0; i < list.length; i++) {
				map[list[i].id_renta] = Number(counts[i] ?? 0) || 0;
			}
			this.unreadByRentaId = map;
		});
	}

	unread(idRenta: number): number {
		return Number(this.unreadByRentaId?.[idRenta] ?? 0) || 0;
	}

	verResumen(idRenta: number): void {
		this.router.navigate(['/rentas/resumen', idRenta]);
	}

	abrirChat(idRenta: number): void {
		this.router.navigate(['/rentas/resumen', idRenta], { queryParams: { chat: 1 }, fragment: 'chat' });
	}

	miniTimeline(r: InboxItem): MiniStep[] {
		const estado = String(r?.estado || '').toLowerCase();
		const isCancel = estado === 'cancelada' || estado === 'expirada';
		const isIncident = estado === 'incidente';
		const isFinal = estado === 'finalizada';

		const order: Record<string, number> = {
			pendiente_pago: 0,
			pagada: 1,
			confirmada: 2,
			en_uso: 3,
			devuelta: 4,
			finalizada: 5,
			incidente: 6,
			cancelada: 7,
			expirada: 7,
		};

		const current = order[estado] ?? 0;
		const done = (key: string) => current >= (order[key] ?? 0);

		const lastLabel = isIncident ? 'Incidente' : isCancel ? (estado === 'expirada' ? 'Expirada' : 'Cancelada') : 'Finalizada';
		const lastKey = isIncident ? 'incidente' : isCancel ? estado : 'finalizada';
		const lastDate = isIncident ? (r.fecha_incidente ?? null) : isCancel ? (r.fecha_cancelacion ?? null) : (r.fecha_finalizacion ?? null);

		const steps: MiniStep[] = [
			{ key: 'pagada', label: 'Pagada', done: done('pagada') || isFinal || isCancel || isIncident, date: r.fecha_pago ?? null },
			{ key: 'confirmada', label: 'Entrega', done: done('confirmada') || isFinal || isCancel || isIncident, date: r.fecha_entrega ?? null },
			{ key: 'en_uso', label: 'En uso', done: done('en_uso') || isFinal || isCancel || isIncident, date: r.fecha_en_uso ?? null },
			{ key: 'devuelta', label: 'Devuelta', done: done('devuelta') || isFinal || isCancel || isIncident, date: r.fecha_devolucion ?? null },
			{ key: lastKey, label: lastLabel, done: isFinal || isCancel || isIncident, date: lastDate },
		];

		// Compacto: ocultar pasos sin completar y sin fecha si el historial es muy corto.
		const essential = steps.filter((s) => s.done || !!s.date || s.key === lastKey);
		return essential.slice(0, 5);
	}

	private getFecha(r: InboxItem, key: string): string | null {
		const tl = r?.timeline || undefined;
		const direct: any = r as any;
		const v = (tl && (tl as any)[key] != null ? (tl as any)[key] : direct?.[key]) as string | null | undefined;
		return v ?? null;
	}

	historialTimeline(r: InboxItem): HistStep[] {
		const estado = String(r?.estado || '').toLowerCase();
		const isCancel = estado === 'cancelada' || estado === 'expirada';
		const isIncident = estado === 'incidente';
		const isFinal = estado === 'finalizada';

		const fechaPago = this.getFecha(r, 'fecha_pago');
		const fechaCoord = this.getFecha(r, 'fecha_coordinacion_confirmada');
		const fechaEntrega = this.getFecha(r, 'fecha_entrega_confirmada') || this.getFecha(r, 'fecha_entrega');
		const fechaEnUso = this.getFecha(r, 'fecha_en_uso');
		const fechaDev = this.getFecha(r, 'fecha_devolucion');
		const fechaFin = this.getFecha(r, 'fecha_finalizacion') || this.getFecha(r, 'fecha_liberacion_deposito');
		const fechaInc = this.getFecha(r, 'fecha_incidente');
		const fechaCanc = this.getFecha(r, 'fecha_cancelacion');
		const fechaExp = this.getFecha(r, 'fecha_expiracion');

		const depositoLiberado = r.deposito_liberado === true;
		const reembolsoSimulado = r.reembolso_simulado === true;

		const out: HistStep[] = [];
		out.push({ key: 'pagada', label: 'Pagada', date: fechaPago, status: fechaPago ? 'done' : 'pending' });
		out.push({ key: 'coordinacion', label: 'Coordinación confirmada', date: fechaCoord, status: fechaCoord ? 'done' : 'pending' });
		out.push({ key: 'entrega', label: 'Entrega confirmada', date: fechaEntrega, status: fechaEntrega ? 'done' : 'pending' });
		out.push({ key: 'en_uso', label: 'En uso', date: fechaEnUso, status: fechaEnUso ? 'done' : 'pending' });
		out.push({ key: 'devuelta', label: 'Devuelta', date: fechaDev, status: fechaDev ? 'done' : 'pending' });

		if (isFinal) {
			out.push({ key: 'finalizada', label: 'Finalizada', date: fechaFin, status: fechaFin ? 'done' : 'pending' });
			if (depositoLiberado) {
				out.push({ key: 'deposito', label: 'Depósito liberado ✅', date: fechaFin, status: 'done' });
			}
		}

		if (isIncident || !!fechaInc) {
			out.push({ key: 'incidente', label: 'Incidente', date: fechaInc, status: 'alert' });
			// Si hay incidente, el depósito suele quedar retenido hasta resolver
			if (!isFinal && (r.deposito ?? r.monto_deposito ?? 0) > 0) {
				out.push({ key: 'deposito_retenido', label: 'Depósito retenido ⏸️', date: null, status: 'pending' });
			}
		}

		if (isCancel) {
			const label = estado === 'expirada' ? 'Expirada' : 'Cancelada';
			const date = estado === 'expirada' ? fechaExp : fechaCanc;
			out.push({ key: estado, label, date, status: 'done' });
			if (reembolsoSimulado) {
				out.push({ key: 'reembolso', label: 'Reembolso simulado', date: null, status: 'done' });
			}
		}

		// Regla UI: ocultar pasos pendientes "no aplicables" si hay un estado final
		const hasFinalState = isFinal || isIncident || isCancel;
		if (!hasFinalState) return out;
		return out.filter((s) => s.status !== 'pending' || !!s.date);
	}
}
