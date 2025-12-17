import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from 'src/app/core/services/auth.service';
import { ArticuloService } from 'src/app/core/services/articulo.service';
import { Articulo } from 'src/app/core/models/articulo.model';
import { UsuarioRatingResumen, UsuarioService } from 'src/app/core/services/usuario.service';

@Component({
	selector: 'app-detalle-articulo',
	templateUrl: './detalle-articulo.component.html',
	styleUrls: ['./detalle-articulo.component.scss'],
})
export class DetalleArticuloComponent implements OnInit {
	loading = false;
	errorMessage = '';
	loadingOcupacion = false;

	articulo: Articulo | null = null;
	esMio = false;
	propietarioRating: UsuarioRatingResumen | null = null;
	ocupacionProxima: Array<{ inicio: string; fin: string }> = [];

	imagenActivaUrl: string | null = null;

	constructor(
		private readonly route: ActivatedRoute,
		private readonly router: Router,
		private readonly articuloService: ArticuloService,
		private readonly authService: AuthService,
		private readonly usuarioService: UsuarioService
	) {}

	get esAdmin(): boolean {
		const roles = this.authService.getRoles();
		return roles.some((r) => {
			const v = String(r).toUpperCase();
			return v === 'ADMIN' || v === 'ADMINISTRADOR';
		});
	}

	ngOnInit(): void {
		const id = Number(this.route.snapshot.paramMap.get('id'));
		if (!Number.isFinite(id) || id <= 0) {
			this.errorMessage = 'ID de artículo inválido.';
			return;
		}

		this.cargarDetalle(id);
	}

	volver(): void {
		this.router.navigate(['/explorar']);
	}

	rentarAhora(): void {
		if (!this.articulo) return;
		this.router.navigate(['/rentas/crear', this.articulo.id]);
	}

	setImagenActiva(url: string): void {
		this.imagenActivaUrl = url;
	}

	private cargarDetalle(id: number): void {
		this.loading = true;
		this.errorMessage = '';
		this.ocupacionProxima = [];

		this.articuloService.getArticuloPorId(id).subscribe({
			next: (art) => {
				this.articulo = art;
				this.propietarioRating = null;
				const userId = this.authService.getUserId();
				this.esMio = !!userId && Number(art?.id_propietario) === userId;

				this.cargarOcupacionProxima(art.id);

				const ownerId = Number(art?.id_propietario);
				if (Number.isFinite(ownerId) && ownerId > 0) {
					this.usuarioService.obtenerRating(ownerId).subscribe({
						next: (r) => (this.propietarioRating = r),
						error: () => {
							// rating opcional
						},
					});
				}

				const principal = art?.imagenes?.find((i) => i.es_principal)?.url_imagen;
				this.imagenActivaUrl = principal || art?.imagen_principal_url || art?.imagenes?.[0]?.url_imagen || null;

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

				this.errorMessage =
					err?.error?.message || 'No se pudo cargar el detalle del artículo.';
			},
		});
	}

	private cargarOcupacionProxima(idArticulo: number): void {
		this.loadingOcupacion = true;
		const hoy = new Date();
		const hasta = new Date(hoy);
		hasta.setDate(hasta.getDate() + 30);

		const toYMDLocal = (d: Date) => {
			const pad = (n: number) => String(n).padStart(2, '0');
			return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
		};

		this.articuloService.getOcupacion(idArticulo, toYMDLocal(hoy), toYMDLocal(hasta)).subscribe({
			next: (ocupado) => {
				this.ocupacionProxima = ocupado ?? [];
				this.loadingOcupacion = false;
			},
			error: () => {
				this.loadingOcupacion = false;
				this.ocupacionProxima = [];
			},
		});
	}
}

