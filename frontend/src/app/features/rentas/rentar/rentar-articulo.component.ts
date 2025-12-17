import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, Validators } from '@angular/forms';
import { ArticuloService } from 'src/app/core/services/articulo.service';
import { AuthService } from 'src/app/core/services/auth.service';
import { Articulo } from 'src/app/core/models/articulo.model';
import { RentaService } from 'src/app/core/services/renta.service';
import { ModalidadRenta } from 'src/app/core/models/renta.model';

@Component({
  selector: 'app-rentar-articulo',
  templateUrl: './rentar-articulo.component.html',
  styleUrls: ['./rentar-articulo.component.scss'],
})
export class RentarArticuloComponent implements OnInit {
  loading = false;
  errorMessage = '';
  requiresProfile = false;
	adminBlocked = false;

  gateOpen = false;
  gateMissing: string[] = [];
  gateSendingVerification = false;
  gateMessage = '';

  ocupacion: Array<{ inicio: string; fin: string }> = [];

  articulo: Articulo | null = null;
  esMio = false;
  modalidad: ModalidadRenta = 'dias';
  permiteHoras = false;
  permiteDias = true;

  form = this.fb.group({
    fecha_inicio: ['', [Validators.required]],
    fecha_fin: ['', [Validators.required]],
  });

  constructor(
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly fb: FormBuilder,
    private readonly articuloService: ArticuloService,
    private readonly authService: AuthService,
    private readonly rentaService: RentaService
  ) {}

  ngOnInit(): void {
    if (this.esAdmin) {
      this.adminBlocked = true;
      return;
    }
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!Number.isFinite(id) || id <= 0) {
      this.errorMessage = 'ID de artículo inválido.';
      return;
    }
    this.cargarArticulo(id);
  }

  get esAdmin(): boolean {
    const roles = this.authService.getRoles();
    return roles.some((r) => {
      const v = String(r).toUpperCase();
      return v === 'ADMIN' || v === 'ADMINISTRADOR';
    });
  }

  irAExplorar(): void {
    this.router.navigate(['/explorar']);
  }

  volverDetalle(): void {
    if (!this.articulo) {
      this.router.navigate(['/explorar']);
      return;
    }
    this.router.navigate(['/articulos', this.articulo.id]);
  }

  confirmarRenta(): void {
    if (this.adminBlocked) {
      this.errorMessage = 'Acción no disponible para administradores.';
      return;
    }
    this.errorMessage = '';
    this.requiresProfile = false;
    this.ocupacion = [];
    if (!this.articulo) return;

    this.gateOpen = false;
    this.gateMissing = [];
    this.gateMessage = '';

    const articuloId = this.articulo.id;

    if (this.esMio) {
      this.errorMessage = 'No puedes rentar tu propio artículo.';
      return;
    }

    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.errorMessage = 'Completa las fechas.';
      return;
    }

    const inicioRaw = (this.form.value.fecha_inicio as string) ?? '';
    const finRaw = (this.form.value.fecha_fin as string) ?? '';

    const inicio = new Date(inicioRaw);
    const fin = new Date(finRaw);
    if (!(inicio instanceof Date) || isNaN(inicio.getTime()) || isNaN(fin.getTime())) {
      this.errorMessage = 'Fechas inválidas.';
      return;
    }

    if (this.modalidad === 'horas') {
      if (inicio.getMinutes() !== 0 || fin.getMinutes() !== 0) {
        this.errorMessage = 'Solo se permiten horas exactas (sin minutos).';
        return;
      }
      const diffMs = fin.getTime() - inicio.getTime();
      if (diffMs < 60 * 60 * 1000) {
        this.errorMessage = 'La renta por horas debe ser de al menos 1 hora.';
        return;
      }
      if (diffMs % (60 * 60 * 1000) !== 0) {
        this.errorMessage = 'Solo se permiten horas exactas (sin minutos).';
        return;
      }
    }

    if (fin <= inicio) {
      this.errorMessage = 'La fecha fin debe ser posterior a la fecha inicio.';
      return;
    }

    this.validarGateAntesDeRentar(() => this.continuarConfirmarRenta(articuloId, inicio, fin));
  }

  private continuarConfirmarRenta(articuloId: number, inicio: Date, fin: Date): void {
    this.loading = true;

    const toYMDLocal = (d: Date) => {
      const pad = (n: number) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    };

    this.articuloService.getOcupacion(articuloId, toYMDLocal(inicio), toYMDLocal(fin)).subscribe({
      next: (ocupado) => {
        this.ocupacion = ocupado;

        const overlaps = (ocupado ?? []).filter((o) => {
          const oInicio = new Date(o.inicio);
          const oFin = new Date(o.fin);
          if (isNaN(oInicio.getTime()) || isNaN(oFin.getTime())) return false;
          return inicio < oFin && fin > oInicio;
        });

        if (overlaps.length > 0) {
          this.loading = false;
          this.errorMessage = 'El artículo no está disponible en el rango seleccionado.';
          return;
        }

        this.rentaService
          .crearRenta({
            id_articulo: articuloId,
            fecha_inicio: inicio.toISOString(),
            fecha_fin: fin.toISOString(),
            modalidad: this.modalidad,
          })
          .subscribe({
            next: (r) => {
              this.loading = false;
              const idRenta = r.id_renta ?? r.id;
              this.router.navigate(['/rentas/resumen', idRenta]);
            },
            error: (err) => {
              this.loading = false;
              const status = err?.status;
              const hasToken = !!this.authService.getToken();
              if ((status === 401 || status === 422) && !hasToken) {
                this.router.navigate(['/login']);
                return;
              }

              if (status === 403 && err?.error?.payload?.code === 'PROFILE_INCOMPLETE') {
                this.abrirGateModal(err?.error?.payload?.missing ?? []);
                return;
              }
				if (status === 403 && err?.error?.payload?.code === 'ADMIN_FORBIDDEN') {
					this.errorMessage = 'Acción no disponible para administradores.';
					this.adminBlocked = true;
					return;
				}
              this.errorMessage = err?.error?.message || 'No se pudo crear la renta.';
            },
          });
      },
      error: (err) => {
        // Si falla ocupación, no bloqueamos el flujo: dejamos que backend valide traslapes.
        this.rentaService
          .crearRenta({
            id_articulo: articuloId,
            fecha_inicio: inicio.toISOString(),
            fecha_fin: fin.toISOString(),
            modalidad: this.modalidad,
          })
          .subscribe({
            next: (r) => {
              this.loading = false;
              const idRenta = r.id_renta ?? r.id;
              this.router.navigate(['/rentas/resumen', idRenta]);
            },
            error: (err2) => {
              this.loading = false;
              const status = err2?.status;
              const hasToken = !!this.authService.getToken();
              if ((status === 401 || status === 422) && !hasToken) {
                this.router.navigate(['/login']);
                return;
              }

              if (status === 403 && err2?.error?.payload?.code === 'PROFILE_INCOMPLETE') {
                this.abrirGateModal(err2?.error?.payload?.missing ?? []);
                return;
              }
				if (status === 403 && err2?.error?.payload?.code === 'ADMIN_FORBIDDEN') {
					this.errorMessage = 'Acción no disponible para administradores.';
					this.adminBlocked = true;
					return;
				}
              this.errorMessage = err2?.error?.message || 'No se pudo crear la renta.';
            },
          });
      },
    });
  }

  private validarGateAntesDeRentar(onOk: () => void): void {
    if (!this.authService.getToken()) {
      this.router.navigate(['/login']);
      return;
    }

    this.authService.me().subscribe({
      next: (resp) => {
        const me: any = resp?.data;
        const missing: string[] = [];
        const emailOk = !!(me?.email_verificado ?? me?.verificado);
        if (!emailOk) missing.push('correo_verificado');
        const tel = String(me?.telefono ?? '').trim();
        if (!tel) missing.push('telefono');
        const ciudad = String(me?.ciudad ?? '').trim();
        const estado = String(me?.estado ?? '').trim();
        const pais = String(me?.pais ?? '').trim();
        if (!(ciudad && estado && pais)) missing.push('ubicacion');

        if (missing.length > 0) {
          this.abrirGateModal(missing);
          return;
        }
        onOk();
      },
      error: () => {
        // Si falla el pre-check, dejamos que backend valide.
        onOk();
      },
    });
  }

  private abrirGateModal(missing: any): void {
    this.gateMissing = Array.isArray(missing) ? missing.map((x) => String(x)) : [];
    this.gateOpen = true;
    this.gateMessage = '';
  }

  cerrarGateModal(): void {
    this.gateOpen = false;
  }

  gateIrAPerfil(): void {
    this.gateOpen = false;
    this.router.navigate(['/perfil']);
  }

  gateEnviarVerificacion(): void {
    this.gateMessage = '';
    if (this.gateSendingVerification) return;
    this.gateSendingVerification = true;
    this.authService.enviarVerificacionEmail().subscribe({
      next: (resp) => {
        this.gateSendingVerification = false;
        this.gateMessage = resp?.message || 'Link de verificación enviado.';
      },
      error: (err) => {
        this.gateSendingVerification = false;
        this.gateMessage = err?.error?.message || 'No se pudo enviar el link de verificación.';
      },
    });
  }

  irAPerfil(): void {
    this.router.navigate(['/perfil']);
  }

  private cargarArticulo(id: number): void {
    this.loading = true;
    this.articuloService.getArticuloPorId(id).subscribe({
      next: (art) => {
        this.articulo = art;
        const userId = this.authService.getUserId();
        this.esMio = !!userId && Number(art?.id_propietario) === userId;

        const precioHora = Number(art?.precio_renta_hora ?? NaN);
        const precioDia = Number(art?.precio_renta_dia ?? NaN);
        this.permiteHoras = Number.isFinite(precioHora) && precioHora > 0;
        this.permiteDias = Number.isFinite(precioDia) && precioDia > 0;

        // fallback: legacy artículos por hora sin precio_renta_hora
        if (!this.permiteHoras && art?.unidad_precio === 'por_hora') {
          const legacy = Number(art?.precio_renta_dia ?? NaN);
          this.permiteHoras = Number.isFinite(legacy) && legacy > 0;
        }

        if (this.permiteDias) {
          this.modalidad = 'dias';
        } else if (this.permiteHoras) {
          this.modalidad = 'horas';
        } else {
          this.modalidad = 'dias';
        }
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
        this.errorMessage = err?.error?.message || 'No se pudo cargar el artículo.';
      },
    });
  }

  onModalidadChange(value: string): void {
    this.modalidad = value === 'horas' ? 'horas' : 'dias';

    if (this.modalidad !== 'horas') return;

    // UX: si ya hay valores, intentar llevarlos a hora exacta (minutos=00)
    const inicioRaw = (this.form.value.fecha_inicio as string) ?? '';
    const finRaw = (this.form.value.fecha_fin as string) ?? '';

    const inicio = inicioRaw ? new Date(inicioRaw) : null;
    const fin = finRaw ? new Date(finRaw) : null;

    const roundToHour = (d: Date) => {
      const copy = new Date(d);
      copy.setMinutes(0, 0, 0);
      return copy;
    };

    const toLocalInputValue = (d: Date) => {
      const pad = (n: number) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    };

    const patch: any = {};
    if (inicio && !isNaN(inicio.getTime())) {
      patch.fecha_inicio = toLocalInputValue(roundToHour(inicio));
    }
    if (fin && !isNaN(fin.getTime())) {
      patch.fecha_fin = toLocalInputValue(roundToHour(fin));
    }
    if (Object.keys(patch).length > 0) {
      this.form.patchValue(patch);
    }
  }
}
