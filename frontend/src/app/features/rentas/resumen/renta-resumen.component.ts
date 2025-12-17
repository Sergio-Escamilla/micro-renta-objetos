import { Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { RentaService } from 'src/app/core/services/renta.service';
import { RentaResumen } from 'src/app/core/models/renta.model';
import { AuthService } from 'src/app/core/services/auth.service';
import { FormControl, Validators } from '@angular/forms';
import { Observable, Subscription, firstValueFrom, interval, startWith, switchMap } from 'rxjs';
import { BadgeService } from 'src/app/core/services/badge.service';
import { PuntoEntregaPublico, PuntoEntregaService } from 'src/app/core/services/punto-entrega.service';

@Component({
  selector: 'app-renta-resumen',
  templateUrl: './renta-resumen.component.html',
  styleUrls: ['./renta-resumen.component.scss'],
})
export class RentaResumenComponent implements OnInit, OnDestroy {
  loading = false;
  paying = false;
  downloadingRecibo = false;
  processingMessage = '';
  errorMessage = '';
  successMessage = '';

  renta: RentaResumen | null = null;

  showIncidente = false;
  incidenteControl = new FormControl('', [Validators.required, Validators.minLength(5)]);

  showCancelar = false;
  cancelarMotivoControl = new FormControl('', [Validators.maxLength(200)]);

  ratingSupported: boolean | null = null;
  showCalificar = false;
  miCalificacion: any | null = null;
  estrellas = 5;
  comentarioControl = new FormControl('', [Validators.maxLength(200)]);

  // Resolver incidente (dueño/admin)
  resolverDecisionControl = new FormControl<'liberar' | 'retener_parcial' | 'retener_total'>('liberar', [Validators.required]);
  resolverMontoControl = new FormControl<number | null>(null);
  resolverNotaControl = new FormControl('', [Validators.maxLength(300)]);

  toastMessage = '';
  toastType: 'success' | 'error' | 'info' = 'info';
  private toastTimer: any = null;

  // Coordinación (panel)
  modoEntregaControl = new FormControl<'arrendador' | 'neutral'>('arrendador', [Validators.required]);
	entregaModoControl = new FormControl<'domicilio' | 'punto_entrega'>('domicilio', [Validators.required]);
	puntoEntregaFiltroControl = new FormControl('', [Validators.maxLength(120)]);
	puntoEntregaIdControl = new FormControl<string>('', []);

	puntosEntrega: PuntoEntregaPublico[] = [];
	puntosEntregaLoading = false;
	puntosEntregaError = '';

  zonaPublicaControl = new FormControl('', [Validators.maxLength(120)]);
  direccionEntregaControl = new FormControl('', [Validators.maxLength(300)]);
  ventanasEntregaControl = new FormControl('', [Validators.maxLength(800)]);
  ventanasDevolucionControl = new FormControl('', [Validators.maxLength(800)]);

  ventanaEntregaElegidaControl = new FormControl('', [Validators.required]);
  ventanaDevolucionElegidaControl = new FormControl('', [Validators.required]);

  // Chat (polling)
  chatMessages: Array<{ id: number; id_emisor: number; mensaje: string; created_at?: string | null }> = [];
  chatInputControl = new FormControl('', [Validators.required, Validators.maxLength(240)]);
  private chatSub: Subscription | null = null;
  @ViewChild('chatScroll', { static: false }) chatScroll?: ElementRef<HTMLDivElement>;

	private shouldFocusChat = false;

  // OTP (dueño valida)
  otpEntregaControl = new FormControl('', [Validators.required, Validators.minLength(6), Validators.maxLength(6)]);
  checklistEntregaControl = new FormControl('', [Validators.maxLength(800)]);
  otpDevolucionControl = new FormControl('', [Validators.required, Validators.minLength(6), Validators.maxLength(6)]);
  checklistDevolucionControl = new FormControl('', [Validators.maxLength(800)]);

  constructor(
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly rentaService: RentaService,
    private readonly authService: AuthService,
		private readonly badgeService: BadgeService,
		private readonly puntoEntregaService: PuntoEntregaService
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!Number.isFinite(id) || id <= 0) {
      this.errorMessage = 'ID de renta inválido.';
      return;
    }

		const q = this.route.snapshot.queryParamMap.get('chat');
		const frag = this.route.snapshot.fragment;
		this.shouldFocusChat = q === '1' || q === 'true' || frag === 'chat';

    this.entregaModoControl.valueChanges.subscribe((v) => {
      if (v === 'punto_entrega') {
        this.cargarPuntosEntregaSiHaceFalta();
      }
    });

    this.cargarRenta(id);
  }

  ngOnDestroy(): void {
    this.detenerChatPolling();
  }

  get subtotal(): number {
    const r = this.renta;
    if (!r) return 0;
    return (typeof r.subtotal_renta === 'number' ? r.subtotal_renta : r.precio_total_renta) || 0;
  }

  get deposito(): number {
    const r = this.renta;
    if (!r) return 0;
    return (typeof r.monto_deposito === 'number' ? r.monto_deposito : 0) || 0;
  }

  get total(): number {
    const r = this.renta;
    if (!r) return 0;
    return (typeof r.total_a_pagar === 'number' ? r.total_a_pagar : this.subtotal + this.deposito) || 0;
  }

  get depositoMensaje(): string {
    if (!this.renta) return '';
    if (this.estadoNormalizado === 'incidente') return 'Depósito en revisión ⏸️';

    const decision = this.renta.incidente?.decision;
    const retenido = this.renta.incidente?.monto_retenido;
    if ((decision === 'retener_parcial' || decision === 'retener_total') && typeof retenido === 'number' && retenido > 0) {
      return `Depósito retenido: $${retenido} ✅`;
    }
    if (this.renta.deposito_liberado) return 'Depósito liberado ✅';
    if (this.deposito > 0) return 'Depósito en garantía';
    return 'Sin depósito';
  }

  formatMoney(v: any): string {
    const n = typeof v === 'string' ? Number(v) : v;
    if (typeof n !== 'number' || !Number.isFinite(n)) return '-';
    return `$${Math.round(n) === n ? n : n.toFixed(2)}`;
  }

  incidenteDecisionLabel(v: any): string {
    const s = String(v ?? '').trim();
    if (s === 'liberar') return 'Liberar depósito';
    if (s === 'retener_parcial') return 'Retener parcial';
    if (s === 'retener_total') return 'Retener total';
    return s || '-';
  }

  get esExpirada(): boolean {
    return !!this.renta && this.renta.estado_renta === 'expirada';
  }

  get esCancelada(): boolean {
    return !!this.renta && this.renta.estado_renta === 'cancelada';
  }

  get estadoNormalizado():
    | 'pendiente_pago'
    | 'pagada'
    | 'confirmada'
    | 'en_uso'
    | 'devuelta'
    | 'finalizada'
    | 'incidente'
    | 'cancelada'
    | 'expirada'
    | '' {
    const e = String(this.renta?.estado_renta ?? '').toLowerCase().trim();
    return (e as any) || '';
  }

  get puedeCancelar(): boolean {
    if (!this.renta) return false;
    const e = this.renta.estado_renta;
    if (e === 'finalizada' || e === 'incidente' || e === 'en_uso' || e === 'devuelta' || e === 'cancelada' || e === 'expirada') return false;
    if (this.soyArrendatario) return e === 'pendiente_pago' || e === 'pagada' || e === 'confirmada';
    if (this.soyDueno) return e === 'pagada' || e === 'confirmada';
    if (this.soyAdmin) return e === 'pendiente_pago' || e === 'pagada' || e === 'confirmada';
    return false;
  }

  get uiBloqueada(): boolean {
    const e = this.estadoNormalizado;
    return this.paying || this.esExpirada || this.esCancelada || e === 'finalizada';
  }

  get chatVisible(): boolean {
    const r = this.renta;
    if (!r) return false;
    const e = this.estadoNormalizado;
    if (e === 'cancelada' || e === 'expirada' || e === 'finalizada') return false;
    return r.chat_habilitado === true;
  }

  get ventanasEntregaOpciones(): string[] {
    return (this.renta?.ventanas_entrega_propuestas ?? []).filter((v) => !!v);
  }

  get ventanasDevolucionOpciones(): string[] {
    return (this.renta?.ventanas_devolucion_propuestas ?? []).filter((v) => !!v);
  }

  get puedeConfirmarCoordinacion(): boolean {
    const r = this.renta;
    if (!r) return false;
    if (!this.soyDueno) return false;
    if (this.uiBloqueada) return false;
    if (r.estado_renta === 'finalizada' || r.estado_renta === 'cancelada' || r.estado_renta === 'expirada') return false;
    return !!r.ventana_entrega_elegida && !!r.ventana_devolucion_elegida && !r.coordinacion_confirmada;
  }

  get puedeEnviarChat(): boolean {
    const r = this.renta;
    if (!r) return false;
    if (this.uiBloqueada) return false;
    return r.chat_habilitado === true;
  }

  // Matriz exacta (UI)
  get puedePagarAhoraUi(): boolean {
    return this.soyArrendatario && this.estadoNormalizado === 'pendiente_pago' && !this.esExpirada && !this.esCancelada;
  }

  get puedeConfirmarEntregaUi(): boolean {
    return this.soyDueno && this.estadoNormalizado === 'pagada' && !this.uiBloqueada;
  }

  get puedeMarcarEnUsoUi(): boolean {
    return this.soyArrendatario && this.estadoNormalizado === 'confirmada' && !this.uiBloqueada;
  }

  get puedeDevolverUi(): boolean {
    return this.soyArrendatario && this.estadoNormalizado === 'en_uso' && !this.uiBloqueada;
  }

  get puedeFinalizarUi(): boolean {
    return this.soyDueno && this.estadoNormalizado === 'devuelta' && !this.uiBloqueada;
  }

  get puedeReportarIncidenteUi(): boolean {
    // Según tabla: dueño puede opcionalmente reportar incidente en devuelta
    return this.soyDueno && this.estadoNormalizado === 'devuelta' && !this.esExpirada && !this.esCancelada;
  }

	get puedeDescargarRecibo(): boolean {
		const r = this.renta;
		if (!r) return false;
		const e = String(r.estado_renta || '');
		return ['pagada', 'confirmada', 'en_uso', 'devuelta', 'finalizada', 'incidente'].includes(e);
	}

  get puedeConfirmarEntregaOtp(): boolean {
    const r = this.renta;
    if (!r) return false;
    if (!this.soyDueno) return false;
    if (this.uiBloqueada) return false;
    return r.estado_renta === 'pagada' || r.estado_renta === 'confirmada';
  }

  get puedeConfirmarDevolucionOtp(): boolean {
    const r = this.renta;
    if (!r) return false;
    if (!this.soyDueno) return false;
    if (this.uiBloqueada) return false;
    return r.estado_renta === 'en_uso';
  }

  private getFecha(key: string): string | null {
    const r: any = this.renta as any;
    if (!r) return null;
    const tl = (r.timeline ?? null) as { [k: string]: string | null } | null;
    const v = (tl && tl[key] != null ? tl[key] : r[key]) as string | null | undefined;
    return v ?? null;
  }

  get timeline(): Array<{ key: string; label: string; date?: string | null; done: boolean }> {
    const r = this.renta;
    if (!r) return [];

    const estado = String(r.estado_renta || '').toLowerCase();
    const order: Record<string, number> = {
      pendiente_pago: 0,
      pagada: 1,
      confirmada: 2,
      en_uso: 3,
      devuelta: 4,
      finalizada: 5,
    };
    const current = order[estado] ?? 0;

    const fechaPago = this.getFecha('fecha_pago');
    const fechaCoord = this.getFecha('fecha_coordinacion_confirmada');
    const fechaEntrega = this.getFecha('fecha_entrega_confirmada') || (r.fecha_entrega ?? null);
    const fechaEnUso = this.getFecha('fecha_en_uso');
    const fechaDev = this.getFecha('fecha_devolucion') || (r.fecha_devolucion ?? null);
    const fechaFin = this.getFecha('fecha_finalizacion') || this.getFecha('fecha_liberacion_deposito');
    const fechaInc = this.getFecha('fecha_incidente');
    const fechaCanc = this.getFecha('fecha_cancelacion');
    const fechaExp = this.getFecha('fecha_expiracion');

    const items: Array<{ key: string; label: string; date?: string | null; done: boolean }> = [];

    items.push({ key: 'pagada', label: 'Pagada', date: fechaPago, done: !!fechaPago || current >= order['pagada'] });
    items.push({
      key: 'coordinacion',
      label: 'Coordinación confirmada',
      date: fechaCoord,
      done: !!fechaCoord || !!r.coordinacion_confirmada || current >= order['confirmada'],
    });
    items.push({
      key: 'confirmada',
      label: 'Entrega confirmada',
      date: fechaEntrega,
      done: !!fechaEntrega || current >= order['confirmada'],
    });
    items.push({ key: 'en_uso', label: 'En uso', date: fechaEnUso, done: !!fechaEnUso || current >= order['en_uso'] });
    items.push({ key: 'devuelta', label: 'Devuelta', date: fechaDev, done: !!fechaDev || current >= order['devuelta'] });

    if (estado === 'finalizada') {
      items.push({ key: 'finalizada', label: 'Finalizada', date: fechaFin, done: true });
      if (r.deposito_liberado === true) {
        items.push({ key: 'deposito_liberado', label: 'Depósito liberado ✅', date: fechaFin, done: true });
      }
    }

    if (estado === 'incidente' || !!fechaInc) {
      items.push({ key: 'incidente', label: 'Incidente', date: fechaInc, done: true });
    }

    if (estado === 'cancelada') {
      items.push({ key: 'cancelada', label: 'Cancelada', date: fechaCanc, done: true });
      if (r.reembolso_simulado === true) {
        items.push({ key: 'reembolso', label: 'Reembolso simulado', date: null, done: true });
      }
    }

    if (estado === 'expirada') {
      items.push({ key: 'expirada', label: 'Expirada', date: fechaExp, done: true });
      if (r.reembolso_simulado === true) {
        items.push({ key: 'reembolso', label: 'Reembolso simulado', date: null, done: true });
      }
    }

    return items;
  }

  get userId(): number | null {
    return this.authService.getUserId();
  }

  get soyDueno(): boolean {
    const uid = this.userId;
    return !!uid && !!this.renta && Number(this.renta.id_propietario) === uid;
  }

  get soyArrendatario(): boolean {
    const uid = this.userId;
    return !!uid && !!this.renta && Number(this.renta.id_arrendatario) === uid;
  }

  get soyAdmin(): boolean {
    const roles = this.authService.getRoles();
    return roles.some((r) => {
      const v = String(r).toUpperCase();
      return v === 'ADMIN' || v === 'ADMINISTRADOR';
    });
  }

  get esEntregaEnPuntoSeguro(): boolean {
    return (this.entregaModoControl.value ?? 'domicilio') === 'punto_entrega';
  }

  get puntosEntregaFiltrados(): PuntoEntregaPublico[] {
    const q = (this.puntoEntregaFiltroControl.value ?? '').toString().trim().toLowerCase();
    const items = this.puntosEntrega ?? [];
    if (!q) return items;
    return items.filter((p) => {
      const nombre = (p.nombre ?? '').toString().toLowerCase();
      const dir = (p.direccion ?? '').toString().toLowerCase();
      return nombre.includes(q) || dir.includes(q);
    });
  }

  get puedoResolverIncidente(): boolean {
    return !!this.renta && this.renta.estado_renta === 'incidente' && (this.soyDueno || this.soyAdmin);
  }

  toggleIncidente(): void {
    if (!this.renta) return;
    if (!this.puedeReportarIncidenteUi) return;
    if (this.paying) return;
    this.showIncidente = !this.showIncidente;
    this.errorMessage = '';
    this.successMessage = '';
    if (!this.showIncidente) {
      this.incidenteControl.reset('');
    }
  }

  toggleCancelar(): void {
    if (!this.renta) return;
    if (!this.puedeCancelar) return;
    this.showCancelar = !this.showCancelar;
    this.errorMessage = '';
    this.successMessage = '';
    if (!this.showCancelar) {
      this.cancelarMotivoControl.reset('');
    }
  }

  confirmarCancelar(): void {
    if (!this.renta) return;
    if (!this.puedeCancelar) return;

    const motivo = (this.cancelarMotivoControl.value ?? '').toString().trim();
    if (this.soyDueno && !motivo) {
      this.showToast('error', 'El motivo es obligatorio para el dueño.');
      return;
    }

    const id = this.renta.id_renta ?? this.renta.id;
    this.runAction('Cancelando renta...', () => this.rentaService.cancelar(id, motivo || null), id, 'Renta cancelada.');
    this.showCancelar = false;
    this.cancelarMotivoControl.reset('');
  }

  onSelectEstrellas(n: number): void {
    const v = Math.max(1, Math.min(5, Number(n)));
    this.estrellas = v;
  }

  toggleCalificar(): void {
    if (!this.renta) return;
    if (this.renta.estado_renta !== 'finalizada') return;
    if (!(this.soyArrendatario || this.soyDueno)) return;
    if (this.ratingSupported !== true) return;
    if (this.miCalificacion) return;

    this.showCalificar = !this.showCalificar;
    this.errorMessage = '';
    this.successMessage = '';
  }

  enviarCalificacion(): void {
    if (!this.renta) return;
    const id = this.renta.id_renta ?? this.renta.id;
    this.runAction(
			'Enviando calificación...',
      () => this.rentaService.calificar(id, { estrellas: this.estrellas, comentario: (this.comentarioControl.value ?? '').toString().trim() || null }),
      id,
      'Calificación enviada.'
    );
    this.showCalificar = false;
    this.comentarioControl.reset('');
  }

  resolverIncidente(): void {
    if (!this.renta) return;
    if (!this.puedoResolverIncidente) return;

    const id = this.renta.id_renta ?? this.renta.id;
    const decision = (this.resolverDecisionControl.value || 'liberar') as 'liberar' | 'retener_parcial' | 'retener_total';

    const montoRaw = this.resolverMontoControl.value;
    const monto = typeof montoRaw === 'number' && Number.isFinite(montoRaw) ? montoRaw : null;
    const nota = (this.resolverNotaControl.value ?? '').toString().trim() || null;

    if (decision === 'retener_parcial') {
      if (monto === null || monto <= 0) {
        this.showToast('error', 'Indica un monto retenido válido (mayor a 0).');
        return;
      }
      const dep = this.deposito;
      if (dep > 0 && !(monto < dep)) {
        this.showToast('error', 'El monto retenido debe ser menor al depósito.');
        return;
      }
    }

		if ((decision === 'retener_parcial' || decision === 'retener_total') && !nota) {
			this.showToast('error', 'La nota es obligatoria cuando se retiene el depósito.');
			return;
		}

    this.runAction(
      'Resolviendo incidente...',
      () => this.rentaService.resolverIncidente(id, { decision, monto_retenido: monto, nota }),
      id,
      'Incidente resuelto. Renta finalizada.'
    );
  }

  volverExplorar(): void {
    this.router.navigate(['/explorar']);
  }

  irMisRentas(): void {
    this.router.navigate(['/rentas/mis']);
  }

  pagarAhora(): void {
    if (!this.renta) return;
    if (this.renta.estado_renta !== 'pendiente_pago') return;
    if (this.esExpirada || this.esCancelada) return;
		if (!this.soyArrendatario) return;

    const id = this.renta.id_renta ?? this.renta.id;
		this.runAction('Procesando pago...', () => this.rentaService.pagarRenta(id), id, '✅ Pago exitoso. La renta quedó como pagada.');
  }

  descargarRecibo(): void {
    if (!this.renta) return;
    if (!this.puedeDescargarRecibo) return;
    if (this.downloadingRecibo) return;

    const id = this.renta.id_renta ?? this.renta.id;
    if (!Number.isFinite(id) || id <= 0) return;

    this.downloadingRecibo = true;
    this.rentaService.descargarRecibo(id).subscribe({
      next: (blob) => {
        try {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `recibo-renta-${id}.pdf`;
          document.body.appendChild(a);
          a.click();
          a.remove();
          setTimeout(() => window.URL.revokeObjectURL(url), 1000);
        } catch {
          this.showToast('error', 'No se pudo descargar el recibo.');
        } finally {
          this.downloadingRecibo = false;
        }
      },
      error: (err: any) => {
        this.downloadingRecibo = false;
        const status = err?.status;
        const hasToken = !!this.authService.getToken();
        if ((status === 401 || status === 422) && !hasToken) {
          this.router.navigate(['/login']);
          return;
        }
        this.showToast('error', err?.error?.message || 'No se pudo descargar el recibo.');
      },
    });
  }

  confirmarEntrega(): void {
    if (!this.renta) return;
    const id = this.renta.id_renta ?? this.renta.id;
		this.runAction('Confirmando entrega...', () => this.rentaService.confirmar(id), id, 'Entrega confirmada.');
  }

  marcarEnUso(): void {
    if (!this.renta) return;
    const id = this.renta.id_renta ?? this.renta.id;
		this.runAction('Marcando en uso...', () => this.rentaService.enUso(id), id, 'Renta marcada en uso.');
  }

  devolver(): void {
    if (!this.renta) return;
    const id = this.renta.id_renta ?? this.renta.id;
		this.runAction('Registrando devolución...', () => this.rentaService.devolver(id), id, 'Devolución registrada.');
  }

  finalizar(): void {
    if (!this.renta) return;
    const id = this.renta.id_renta ?? this.renta.id;
    this.runAction(
      'Finalizando (liberando depósito)...',
      () => this.rentaService.finalizar(id),
      id,
      'Renta finalizada. Depósito liberado.'
    );
  }

  enviarIncidente(): void {
    if (!this.renta) return;
    if (this.renta.estado_renta === 'finalizada') return;
    this.errorMessage = '';
    this.successMessage = '';

    if (this.incidenteControl.invalid) {
      this.incidenteControl.markAsTouched();
      this.errorMessage = 'Describe el incidente (mín. 5 caracteres).';
      return;
    }

    const id = this.renta.id_renta ?? this.renta.id;
    const descripcion = String(this.incidenteControl.value ?? '').trim();
		this.runAction('Enviando incidente...', () => this.rentaService.incidente(id, descripcion), id, 'Incidente reportado.');
    this.showIncidente = false;
    this.incidenteControl.reset('');
  }

  private cargarRenta(id: number): void {
    this.loading = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.rentaService.obtenerRenta(id).subscribe({
      next: (r) => {
				this.aplicarRenta(r, id);
				this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        const status = err?.status;
        const hasToken = !!this.authService.getToken();
        if ((status === 401 || status === 422) && !hasToken) {
          this.router.navigate(['/login']);
          return;
        }
        this.errorMessage = err?.error?.message || 'No se pudo cargar el resumen de la renta.';
        this.showToast('error', this.errorMessage);
      },
    });
  }

  private refrescar(id: number): void {
    this.rentaService.obtenerRenta(id).subscribe({
      next: (r) => {
        this.aplicarRenta(r, id);
      },
      error: () => {
        // no rompe UX si el refresh falla
      },
    });
  }

  private aplicarRenta(r: RentaResumen, id: number): void {
    this.renta = r;
    this.sincronizarFormulariosConRenta();
    this.iniciarChatPollingSiCorresponde(id);
    this.marcarChatLeidoSiCorresponde(id);
    this.scrollASiCorresponde();

    // Cerrar paneles si ya no aplican
    if (!this.puedeCancelar) this.showCancelar = false;
    if (!this.puedeReportarIncidenteUi) this.showIncidente = false;

    // Calificaciones (solo si aplica)
    if (this.renta.estado_renta === 'finalizada' && (this.soyArrendatario || this.soyDueno)) {
      this.cargarMiCalificacion(id);
    } else {
      this.ratingSupported = null;
      this.showCalificar = false;
      this.miCalificacion = null;
    }
  }

  private async recargarRentaAsync(idRenta: number): Promise<void> {
    const r = await firstValueFrom(this.rentaService.obtenerRenta(idRenta));
    this.aplicarRenta(r, idRenta);
  }

  private runAction(
    actionName: string,
    httpCall: () => Observable<any>,
    idRenta: number,
    successMsg: string
  ): void {
    if (this.paying) return;
    this.errorMessage = '';
    this.successMessage = '';
    this.paying = true;
    this.processingMessage = actionName;

    ( async () => {
      try {
        await firstValueFrom(httpCall());
        await this.recargarRentaAsync(idRenta);
        this.successMessage = successMsg;
        this.showToast('success', successMsg || 'Listo.');
        this.badgeService.refreshOnce();
      } catch (err: any) {
        const status = err?.status;
        const hasToken = !!this.authService.getToken();
        if ((status === 401 || status === 422) && !hasToken) {
          this.router.navigate(['/login']);
          return;
        }

        if (status === 409) {
          this.showToast('info', 'La renta ya cambió de estado, se recargará.');
          try {
            await this.recargarRentaAsync(idRenta);
            this.badgeService.refreshOnce();
          } catch {
            // best-effort
          }
          return;
        }

        if (status === 403) {
          this.errorMessage = 'No tienes permiso para realizar esta acción.';
          this.showToast('error', this.errorMessage);
          return;
        }

        this.errorMessage = err?.error?.message || 'No se pudo completar la acción.';
        this.showToast('error', this.errorMessage);
      } finally {
        this.paying = false;
        this.processingMessage = '';
      }
    })();
  }

  private sincronizarFormulariosConRenta(): void {
    const r = this.renta;
    if (!r) return;

    // Dueño: precargar valores
    this.modoEntregaControl.setValue(((r.modo_entrega as any) || 'arrendador') === 'neutral' ? 'neutral' : 'arrendador', { emitEvent: false });
		this.entregaModoControl.setValue(((r.entrega_modo as any) || 'domicilio') === 'punto_entrega' ? 'punto_entrega' : 'domicilio', {
			emitEvent: false,
		});
		this.puntoEntregaIdControl.setValue((r.punto_entrega?.id != null ? String(r.punto_entrega.id) : '') as any, { emitEvent: false });
    this.zonaPublicaControl.setValue((r.zona_publica ?? '') as any, { emitEvent: false });
    this.direccionEntregaControl.setValue((r.direccion_entrega ?? '') as any, { emitEvent: false });

    const ve = (r.ventanas_entrega_propuestas ?? []).join('\n');
    const vd = (r.ventanas_devolucion_propuestas ?? []).join('\n');
    this.ventanasEntregaControl.setValue(ve, { emitEvent: false });
    this.ventanasDevolucionControl.setValue(vd, { emitEvent: false });

    // Arrendatario: precargar selección
    this.ventanaEntregaElegidaControl.setValue((r.ventana_entrega_elegida ?? '') as any, { emitEvent: false });
    this.ventanaDevolucionElegidaControl.setValue((r.ventana_devolucion_elegida ?? '') as any, { emitEvent: false });

    // Si aplica, cargar el catálogo de puntos seguros.
    if (this.soyDueno && ((r.entrega_modo as any) || 'domicilio') === 'punto_entrega') {
      this.cargarPuntosEntregaSiHaceFalta();
    }
  }

  cargarPuntosEntregaSiHaceFalta(): void {
    if (this.puntosEntregaLoading) return;
    if ((this.puntosEntrega?.length ?? 0) > 0) return;
    this.puntosEntregaError = '';
    this.puntosEntregaLoading = true;
    this.puntoEntregaService.listarActivos().subscribe({
      next: (items) => {
        this.puntosEntrega = items ?? [];
        this.puntosEntregaLoading = false;
      },
      error: (err) => {
        this.puntosEntregaLoading = false;
        this.puntosEntregaError = err?.error?.message || 'No se pudieron cargar los puntos seguros.';
        this.showToast('info', this.puntosEntregaError);
      },
    });
  }

  private iniciarChatPollingSiCorresponde(idRenta: number): void {
    if (!this.renta || this.renta.chat_habilitado !== true || this.uiBloqueada) {
      this.detenerChatPolling();
      return;
    }

    if (this.chatSub) return;

    this.chatSub = interval(7000)
      .pipe(
        startWith(0),
        switchMap(() => this.rentaService.getChat(idRenta))
      )
      .subscribe({
        next: (items) => {
          this.chatMessages = items || [];
          this.scrollChatAbajo();
        },
        error: () => {
          // silencioso: no rompe UX
        },
      });
  }

  private scrollASiCorresponde(): void {
    if (!this.shouldFocusChat) return;
    if (!this.renta || this.renta.chat_habilitado !== true) return;
    setTimeout(() => {
      try {
        document.getElementById('chat')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } catch {
        // ignore
      }
    }, 0);
  }

  private marcarChatLeidoSiCorresponde(idRenta: number): void {
    if (!this.renta || this.renta.chat_habilitado !== true) return;
    this.rentaService.chatMarcarLeido(idRenta).subscribe({
      next: () => {
        // no-op
      },
      error: () => {
        // silencioso
      },
    });
  }

  private detenerChatPolling(): void {
    if (this.chatSub) {
      this.chatSub.unsubscribe();
      this.chatSub = null;
    }
  }

  private scrollChatAbajo(): void {
    if (!this.chatScroll?.nativeElement) return;
    setTimeout(() => {
      try {
        const el = this.chatScroll?.nativeElement;
        if (!el) return;
        el.scrollTop = el.scrollHeight;
      } catch {
        // ignore
      }
    }, 0);
  }

  guardarCoordinacion(): void {
    if (!this.renta) return;
    if (!this.soyDueno) return;
    if (this.uiBloqueada) return;

    const id = this.renta.id_renta ?? this.renta.id;

    const modo = this.modoEntregaControl.value || 'arrendador';
    const entrega_modo = this.entregaModoControl.value || 'domicilio';
    let id_punto_entrega: number | null = null;
    let zona_publica = (this.zonaPublicaControl.value ?? '').toString().trim() || null;
    let direccion_entrega = (this.direccionEntregaControl.value ?? '').toString().trim() || null;
    if (entrega_modo === 'punto_entrega') {
      const raw = (this.puntoEntregaIdControl.value ?? '').toString().trim();
      const parsed = raw ? Number(raw) : NaN;
      if (!Number.isFinite(parsed) || parsed <= 0) {
        this.showToast('error', 'Elige un punto seguro.');
        return;
      }
      id_punto_entrega = parsed;
      zona_publica = null;
      direccion_entrega = null;
    }

    const ventanasEntrega = (this.ventanasEntregaControl.value ?? '')
      .toString()
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);
    const ventanasDevolucion = (this.ventanasDevolucionControl.value ?? '')
      .toString()
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);

    this.ejecutarAccion(
      'Guardando coordinación...',
      () =>
        this.rentaService.coordinar(id, {
          modo_entrega: modo,
				entrega_modo,
				id_punto_entrega,
          zona_publica,
          direccion_entrega,
          ventanas_entrega_propuestas: ventanasEntrega.length ? ventanasEntrega : null,
          ventanas_devolucion_propuestas: ventanasDevolucion.length ? ventanasDevolucion : null,
        }),
      id,
      'Coordinación actualizada.'
    );
  }

  confirmarCoordinacion(): void {
    if (!this.renta) return;
    if (!this.puedeConfirmarCoordinacion) return;
    const id = this.renta.id_renta ?? this.renta.id;
    this.ejecutarAccion(
      'Confirmando coordinación...',
      () => this.rentaService.coordinar(id, { confirmar: true }),
      id,
      'Coordinación confirmada.'
    );
  }

  aceptarCoordinacion(): void {
    if (!this.renta) return;
    if (!this.soyArrendatario) return;
    if (this.uiBloqueada) return;

    const ve = (this.ventanaEntregaElegidaControl.value ?? '').toString().trim();
    const vd = (this.ventanaDevolucionElegidaControl.value ?? '').toString().trim();
    if (!ve || !vd) {
      this.showToast('error', 'Elige ventana de entrega y devolución.');
      return;
    }

    const id = this.renta.id_renta ?? this.renta.id;
    this.ejecutarAccion(
      'Aceptando coordinación...',
      () => this.rentaService.aceptarCoordinacion(id, { ventana_entrega: ve, ventana_devolucion: vd }),
      id,
      'Coordinación aceptada.'
    );
  }

  enviarChat(): void {
    if (!this.renta) return;
    if (!this.puedeEnviarChat) return;

    const msg = (this.chatInputControl.value ?? '').toString().trim();
    if (!msg) {
      this.showToast('error', 'Escribe un mensaje.');
      return;
    }

    const id = this.renta.id_renta ?? this.renta.id;
    this.paying = true;
    this.processingMessage = 'Enviando mensaje...';
    this.rentaService.sendChatMessage(id, msg).subscribe({
      next: () => {
        this.paying = false;
        this.processingMessage = '';
        this.chatInputControl.reset('');
        // Refrescar chat una vez
        this.rentaService.getChat(id).subscribe({
          next: (items) => {
            this.chatMessages = items || [];
            this.scrollChatAbajo();
          },
          error: () => {
            // ignore
          },
        });
      },
      error: (err) => {
        this.paying = false;
        this.processingMessage = '';
        const status = err?.status;
        if (status === 429) {
          const m = err?.error?.message || 'Estás enviando muy rápido. Intenta de nuevo en unos segundos.';
          this.showToast('error', m);
          return;
        }

        const m = err?.error?.message || 'No se pudo enviar el mensaje.';
        this.showToast('error', m);
      },
    });
  }

  confirmarEntregaOtp(): void {
    if (!this.renta) return;
    if (!this.puedeConfirmarEntregaOtp) return;

    const codigo = (this.otpEntregaControl.value ?? '').toString().trim();
    const checklist = (this.checklistEntregaControl.value ?? '').toString().trim() || null;
    const id = this.renta.id_renta ?? this.renta.id;
    this.ejecutarAccion(
      'Confirmando entrega (OTP)...',
      () => this.rentaService.confirmarEntregaOtp(id, { codigo, checklist }),
      id,
      'Entrega confirmada (OTP).'
    );
    this.otpEntregaControl.reset('');
  }

  confirmarDevolucionOtp(): void {
    if (!this.renta) return;
    if (!this.puedeConfirmarDevolucionOtp) return;

    const codigo = (this.otpDevolucionControl.value ?? '').toString().trim();
    const checklist = (this.checklistDevolucionControl.value ?? '').toString().trim() || null;
    const id = this.renta.id_renta ?? this.renta.id;
    this.ejecutarAccion(
      'Confirmando devolución (OTP)...',
      () => this.rentaService.confirmarDevolucionOtp(id, { codigo, checklist }),
      id,
      'Devolución confirmada (OTP).'
    );
    this.otpDevolucionControl.reset('');
  }

  private cargarMiCalificacion(idRenta: number): void {
    this.rentaService.obtenerCalificacion(idRenta).subscribe({
      next: (data) => {
        this.ratingSupported = true;
        this.miCalificacion = data?.calificacion ?? null;
        this.showCalificar = false;
      },
      error: () => {
        // si falla, oculta el panel
        this.ratingSupported = false;
        this.miCalificacion = null;
        this.showCalificar = false;
      },
    });
  }

  private ejecutarAccion(
    processingMsg: string,
    action: () => Observable<any>,
    idRenta: number,
    successMsg: string
  ): void {
    this.errorMessage = '';
    this.successMessage = '';
    this.paying = true;
    this.processingMessage = processingMsg;

    action().subscribe({
      next: () => {
        this.paying = false;
        this.processingMessage = '';
        this.successMessage = successMsg;
        this.showToast('success', successMsg);
        this.refrescar(idRenta);
      },
      error: (err: any) => {
        this.paying = false;
        this.processingMessage = '';
        const status = err?.status;
        const hasToken = !!this.authService.getToken();
        if ((status === 401 || status === 422) && !hasToken) {
          this.router.navigate(['/login']);
          return;
        }
        this.errorMessage = err?.error?.message || 'No se pudo completar la acción.';
        this.showToast('error', this.errorMessage);
      },
    });
  }

  private showToast(type: 'success' | 'error' | 'info', message: string): void {
    this.toastType = type;
    this.toastMessage = message;
    if (this.toastTimer) {
      clearTimeout(this.toastTimer);
      this.toastTimer = null;
    }
    this.toastTimer = setTimeout(() => {
      this.toastMessage = '';
      this.toastTimer = null;
    }, 3500);
  }
}
