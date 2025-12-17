import { Component, OnInit } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from 'src/app/core/services/auth.service';
import { ArticuloService } from 'src/app/core/services/articulo.service';
import { CategoriaService } from 'src/app/core/services/categoria.service';
import { Categoria } from 'src/app/core/models/categoria.model';

@Component({
  selector: 'app-publicar-articulo',
  templateUrl: './publicar-articulo.component.html',
  styleUrls: ['./publicar-articulo.component.scss'],
})
export class PublicarArticuloComponent implements OnInit {
  loading = false;
  errorMessage = '';
  successMessage = '';
  requiresProfile = false;
	adminBlocked = false;

  gateOpen = false;
  gateMissing: string[] = [];
  gateSendingVerification = false;
  gateMessage = '';

  categorias: Categoria[] = [];
  loadingCategorias = false;

  selectedFiles: File[] = [];

  form = this.fb.group({
    titulo: ['', [Validators.required, Validators.maxLength(120)]],
    descripcion: ['', [Validators.required, Validators.maxLength(2000)]],
    id_categoria: [null as number | null, [Validators.required, Validators.min(1)]],
    rentar_por_dias: [true],
    rentar_por_horas: [false],
    precio_renta_dia: [null as number | null, [Validators.min(0)]],
    precio_renta_hora: [null as number | null, [Validators.min(0)]],
    deposito_garantia: [0 as number | null, [Validators.min(0)]],
    ciudad: ['', [Validators.required, Validators.maxLength(80)]],
    ubicacion_texto: ['', [Validators.maxLength(255)]],
  });

  constructor(
    private readonly fb: FormBuilder,
    private readonly articuloService: ArticuloService,
    private readonly categoriaService: CategoriaService,
    private readonly authService: AuthService,
    private readonly router: Router
  ) {}

  ngOnInit(): void {
    if (this.esAdmin) {
      this.adminBlocked = true;
      return;
    }
    this.cargarCategorias();
  }

  get esAdmin(): boolean {
    const roles = this.authService.getRoles();
    return roles.some((r) => {
      const v = String(r).toUpperCase();
      return v === 'ADMIN' || v === 'ADMINISTRADOR';
    });
  }

  irAExplorar(): void {
    this.router.navigateByUrl('/explorar');
  }

  cargarCategorias(): void {
    this.loadingCategorias = true;
    this.categoriaService.getCategorias().subscribe({
      next: (cats) => {
        this.categorias = cats;
        this.loadingCategorias = false;
      },
      error: () => {
        this.loadingCategorias = false;
        // No bloquea el flujo, pero avisamos
        this.errorMessage = 'No se pudieron cargar las categorías.';
      },
    });
  }

  onFilesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = input.files;
    if (!files) {
      this.selectedFiles = [];
      return;
    }

    this.selectedFiles = Array.from(files);
  }

  cancelar(): void {
    this.router.navigateByUrl('/perfil');
  }

  publicar(): void {
		if (this.adminBlocked) {
			this.errorMessage = 'Acción no disponible para administradores.';
			return;
		}
    this.errorMessage = '';
    this.successMessage = '';
    this.requiresProfile = false;

    this.gateOpen = false;
    this.gateMissing = [];
    this.gateMessage = '';

    this.validarGateAntesDePublicar(() => this.publicarInternal());
  }

  private publicarInternal(): void {

    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.errorMessage = 'Revisa los campos del formulario.';
      return;
    }

    const porDias = !!this.form.value.rentar_por_dias;
    const porHoras = !!this.form.value.rentar_por_horas;
    const precioDia = this.form.value.precio_renta_dia;
    const precioHora = this.form.value.precio_renta_hora;

    const diaOk = typeof precioDia === 'number' && Number.isFinite(precioDia) && precioDia > 0;
    const horaOk = typeof precioHora === 'number' && Number.isFinite(precioHora) && precioHora > 0;

    if (!porDias && !porHoras) {
      this.errorMessage = 'Activa al menos una modalidad (días u horas).';
      return;
    }
    if (porDias && !diaOk) {
      this.errorMessage = 'Indica un precio válido por día.';
      return;
    }
    if (porHoras && !horaOk) {
      this.errorMessage = 'Indica un precio válido por hora.';
      return;
    }

    if (this.selectedFiles.length < 1) {
      this.errorMessage = 'Selecciona al menos una imagen.';
      return;
    }

    const payload = {
      titulo: (this.form.value.titulo ?? '').trim(),
      descripcion: (this.form.value.descripcion ?? '').trim(),
      id_categoria: Number(this.form.value.id_categoria),
      // Compat: unidad_precio sigue existiendo, pero ahora soportamos ambas tarifas
      unidad_precio: porHoras && !porDias ? 'por_hora' : 'por_dia',
      precio_renta_dia: porDias && diaOk ? Number(precioDia) : null,
      precio_renta_hora: porHoras && horaOk ? Number(precioHora) : null,
      deposito_garantia: Number(this.form.value.deposito_garantia ?? 0),
      ciudad: (this.form.value.ciudad ?? '').trim(),
      ubicacion_texto: (this.form.value.ubicacion_texto ?? '').trim() || null,
    };

    this.loading = true;
    this.articuloService.crearArticulo(payload).subscribe({
      next: (articulo) => {
        const articuloId = articulo?.id;
        if (!articuloId) {
          this.loading = false;
          this.errorMessage = 'No se pudo obtener el ID del artículo creado.';
          return;
        }

        this.articuloService.subirImagenes(articuloId, this.selectedFiles).subscribe({
          next: () => {
            this.loading = false;
            this.successMessage = 'Artículo publicado.';
            this.router.navigateByUrl('/perfil');
          },
          error: (err) => {
            this.loading = false;
            const status = err?.status;
            if (status === 401 || status === 422) {
              this.authService.logout();
              this.router.navigateByUrl('/login');
              return;
            }
            this.errorMessage =
              err?.error?.message || 'El artículo se creó, pero falló la subida de imágenes.';
          },
        });
      },
      error: (err) => {
        this.loading = false;

        const status = err?.status;
        if (status === 401 || status === 422) {
          this.authService.logout();
          this.router.navigateByUrl('/login');
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

        this.errorMessage =
          err?.error?.message || 'No se pudo publicar el artículo.';
      },
    });
  }

  private validarGateAntesDePublicar(onOk: () => void): void {
    if (!this.authService.getToken()) {
      this.router.navigateByUrl('/login');
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
        // Si falla el pre-check, dejamos que el backend valide.
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
    this.router.navigateByUrl('/perfil');
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
    this.router.navigateByUrl('/perfil');
  }
}
