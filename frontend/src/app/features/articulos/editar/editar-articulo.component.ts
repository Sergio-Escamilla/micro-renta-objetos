import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, Validators } from '@angular/forms';
import { ArticuloService } from 'src/app/core/services/articulo.service';
import { AuthService } from 'src/app/core/services/auth.service';
import { Articulo } from 'src/app/core/models/articulo.model';

@Component({
	selector: 'app-editar-articulo',
	templateUrl: './editar-articulo.component.html',
	styleUrls: ['./editar-articulo.component.scss'],
})
export class EditarArticuloComponent implements OnInit {
	loading = false;
	saving = false;
	uploadingFotos = false;
	workingImagenId: number | null = null;
	reordering = false;
	errorMessage = '';
	toastMessage = '';
	toastType: 'success' | 'error' | 'info' = 'info';
	private toastTimer: any = null;

	articulo: Articulo | null = null;
	selectedFiles: File[] = [];

	form = this.fb.group({
		titulo: ['', [Validators.required, Validators.maxLength(120)]],
		descripcion: ['', [Validators.required, Validators.maxLength(2000)]],
		rentar_por_dias: [true],
		rentar_por_horas: [false],
		precio_renta_dia: [null as number | null, [Validators.min(0)]],
		precio_renta_hora: [null as number | null, [Validators.min(0)]],
		deposito_garantia: [0 as number | null, [Validators.min(0)]],
		estado_publicacion: ['publicado'],
	});

	constructor(
		private readonly route: ActivatedRoute,
		private readonly router: Router,
		private readonly fb: FormBuilder,
		private readonly articuloService: ArticuloService,
		private readonly authService: AuthService
	) {}

	get imagenesOrdenadas(): Array<{ id?: number; url_imagen: string; es_principal: boolean; orden?: number | null }> {
		const imgs = this.articulo?.imagenes ?? [];
		return [...imgs].sort((a, b) => {
			const ao = a.orden ?? 10 ** 9;
			const bo = b.orden ?? 10 ** 9;
			if (ao !== bo) return ao - bo;
			return Number(a.id ?? 0) - Number(b.id ?? 0);
		});
	}

	ngOnInit(): void {
		const id = Number(this.route.snapshot.paramMap.get('id'));
		if (!Number.isFinite(id) || id <= 0) {
			this.errorMessage = 'ID de artículo inválido.';
			return;
		}
		this.cargar(id);
	}

	volver(): void {
		this.router.navigateByUrl('/perfil');
	}

	guardar(): void {
		this.errorMessage = '';

		if (!this.articulo) return;
		if (this.form.invalid) {
			this.form.markAllAsTouched();
			this.errorMessage = 'Revisa los campos del formulario.';
			return;
		}

		const porDias = !!this.form.value.rentar_por_dias;
		const porHoras = !!this.form.value.rentar_por_horas;
		if (!porDias && !porHoras) {
			this.errorMessage = 'Activa al menos una modalidad (días u horas).';
			return;
		}

		const precioDia = this.form.value.precio_renta_dia;
		const precioHora = this.form.value.precio_renta_hora;
		const diaOk = typeof precioDia === 'number' && Number.isFinite(precioDia) && precioDia > 0;
		const horaOk = typeof precioHora === 'number' && Number.isFinite(precioHora) && precioHora > 0;

		if (porDias && !diaOk) {
			this.errorMessage = 'Indica un precio válido por día.';
			return;
		}
		if (porHoras && !horaOk) {
			this.errorMessage = 'Indica un precio válido por hora.';
			return;
		}

		this.saving = true;
		// Nota: la BD real soporta 1 modalidad por artículo (unidad_precio).
		// Si el usuario activa ambas, enviamos unidad_precio como modalidad principal.
		const unidadPrecio = porHoras && !porDias ? 'por_hora' : 'por_dia';
		this.articuloService
			.actualizarArticulo(this.articulo.id, {
				titulo: String(this.form.value.titulo ?? '').trim(),
				descripcion: String(this.form.value.descripcion ?? '').trim(),
				unidad_precio: unidadPrecio,
				precio_renta_dia: porDias && diaOk ? Number(precioDia) : null,
				precio_renta_hora: porHoras && horaOk ? Number(precioHora) : null,
				deposito_garantia: Number(this.form.value.deposito_garantia ?? 0),
				estado_publicacion: String(this.form.value.estado_publicacion ?? 'publicado'),
			})
			.subscribe({
				next: (art) => {
					this.saving = false;
					this.articulo = art;
					this.showToast('success', 'Cambios guardados.');
				},
				error: (err) => {
					this.saving = false;
					const status = err?.status;
					const hasToken = !!this.authService.getToken();
					if ((status === 401 || status === 422) && !hasToken) {
						this.router.navigate(['/login']);
						return;
					}
					this.showToast('error', err?.error?.message || 'No se pudo guardar el artículo.');
				},
			});
	}

	onFilesSelected(ev: Event): void {
		const input = ev.target as HTMLInputElement;
		const files = Array.from(input.files ?? []);
		this.selectedFiles = files;
	}

	agregarFotos(): void {
		this.errorMessage = '';
		if (!this.articulo) return;
		if (!this.selectedFiles.length) {
			this.showToast('info', 'Selecciona al menos una foto.');
			return;
		}
		this.uploadingFotos = true;
		this.articuloService.subirImagenes(this.articulo.id, this.selectedFiles).subscribe({
			next: () => {
				this.uploadingFotos = false;
				this.selectedFiles = [];
				this.showToast('success', 'Fotos agregadas.');
				this.cargar(this.articulo!.id);
			},
			error: (err) => {
				this.uploadingFotos = false;
				this.showToast('error', err?.error?.message || 'No se pudieron subir las fotos.');
			},
		});
	}

	eliminarFoto(img: { id?: number; url_imagen: string }): void {
		if (!this.articulo) return;
		const idImagen = Number(img?.id);
		if (!Number.isFinite(idImagen) || idImagen <= 0) return;
		this.workingImagenId = idImagen;
		this.articuloService.eliminarImagen(this.articulo.id, idImagen).subscribe({
			next: () => {
				this.workingImagenId = null;
				this.showToast('success', 'Foto eliminada.');
				this.cargar(this.articulo!.id);
			},
			error: (err) => {
				this.workingImagenId = null;
				this.showToast('error', err?.error?.message || 'No se pudo eliminar la foto.');
			},
		});
	}

	hacerPortada(img: { id?: number }): void {
		if (!this.articulo) return;
		const idImagen = Number(img?.id);
		if (!Number.isFinite(idImagen) || idImagen <= 0) return;
		this.workingImagenId = idImagen;
		this.articuloService.marcarImagenPrincipal(this.articulo.id, idImagen).subscribe({
			next: () => {
				this.workingImagenId = null;
				this.showToast('success', 'Portada actualizada.');
				this.cargar(this.articulo!.id);
			},
			error: (err) => {
				this.workingImagenId = null;
				this.showToast('error', err?.error?.message || 'No se pudo cambiar la portada.');
			},
		});
	}

	moverFoto(imgId: number, direction: 'up' | 'down'): void {
		if (!this.articulo) return;
		const imgs = (this.articulo.imagenes ?? []).filter((i) => Number.isFinite(Number(i.id)));
		const ordered = [...imgs].sort((a, b) => {
			const ao = a.orden ?? 10 ** 9;
			const bo = b.orden ?? 10 ** 9;
			if (ao !== bo) return ao - bo;
			return (a.id ?? 0) - (b.id ?? 0);
		});
		const idx = ordered.findIndex((i) => Number(i.id) === Number(imgId));
		if (idx < 0) return;
		const swapWith = direction === 'up' ? idx - 1 : idx + 1;
		if (swapWith < 0 || swapWith >= ordered.length) return;

		const tmp = ordered[idx];
		ordered[idx] = ordered[swapWith];
		ordered[swapWith] = tmp;

		const ids = ordered.map((i) => Number(i.id));
		this.reordering = true;
		this.articuloService.reordenarImagenes(this.articulo.id, ids).subscribe({
			next: () => {
				this.reordering = false;
				this.cargar(this.articulo!.id);
			},
			error: (err) => {
				this.reordering = false;
				this.showToast('error', err?.error?.message || 'No se pudo reordenar.');
			},
		});
	}

	private cargar(id: number): void {
		this.loading = true;
		this.errorMessage = '';
		this.articuloService.getArticuloPorId(id).subscribe({
			next: (art) => {
				this.articulo = art;
				const precioDia = Number(art?.precio_renta_dia ?? NaN);
				const precioHora = Number(art?.precio_renta_hora ?? NaN);
				const porDias = Number.isFinite(precioDia) && precioDia > 0;
				const porHoras = Number.isFinite(precioHora) && precioHora > 0;

				this.form.patchValue({
					titulo: String(art?.titulo ?? ''),
					descripcion: String((art as any)?.descripcion ?? ''),
					rentar_por_dias: porDias || !porHoras,
					rentar_por_horas: porHoras,
					precio_renta_dia: porDias ? precioDia : null,
					precio_renta_hora: porHoras ? precioHora : null,
					deposito_garantia: Number((art as any)?.deposito_garantia ?? 0),
					estado_publicacion: String((art as any)?.estado_publicacion ?? 'publicado'),
				});

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
