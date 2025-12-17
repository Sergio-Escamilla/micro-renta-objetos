import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { FormBuilder, Validators } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { ArticuloService } from '../../../core/services/articulo.service';
import { UsuarioRatingResumen, UsuarioResumenMe, UsuarioService } from '../../../core/services/usuario.service';
import { Articulo } from '../../../core/models/articulo.model';
import { Notificacion, NotificacionService } from '../../../core/services/notificacion.service';

@Component({
	selector: 'app-perfil',
	templateUrl: './perfil.component.html',
	styleUrls: ['./perfil.component.scss'],
})
export class PerfilComponent implements OnInit {
	user: any = null;
	rating: UsuarioRatingResumen | null = null;
	articulos: Articulo[] = [];
	notificaciones: Notificacion[] = [];
	unreadCount = 0;
	loadingUser = false;
	sendingVerification = false;
	verificationMessage = '';
	loadingArticulos = false;
	loadingNotificaciones = false;
	loadingResumen = false;
	resumen: UsuarioResumenMe | null = null;
	editMode = false;
	savingProfile = false;
	profileMessage = '';
	errorMessage = '';

	form = this.fb.group({
		nombre: ['', [Validators.required, Validators.maxLength(100)]],
		apellidos: ['', [Validators.required, Validators.maxLength(100)]],
		telefono: ['', [Validators.maxLength(20)]],
		ciudad: ['', [Validators.maxLength(100)]],
		estado: ['', [Validators.maxLength(100)]],
		pais: ['', [Validators.maxLength(100)]],
		direccion_completa: ['', [Validators.maxLength(2000)]],
	});

	constructor(
		private authService: AuthService,
		private articuloService: ArticuloService,
		private usuarioService: UsuarioService,
		private notificacionService: NotificacionService,
		private fb: FormBuilder,
		private router: Router
	) {}

	get esAdmin(): boolean {
		const roles = this.authService.getRoles();
		return roles.some((r) => {
			const v = String(r).toUpperCase();
			return v === 'ADMIN' || v === 'ADMINISTRADOR';
		});
	}

	ngOnInit(): void {
		this.cargarPerfil();
		this.cargarResumen();
		this.cargarMisArticulos();
		this.cargarNotificaciones();
	}

	cargarResumen(): void {
		this.loadingResumen = true;
		this.usuarioService.resumenMe().subscribe({
			next: (r) => {
				this.resumen = r;
				this.loadingResumen = false;
			},
			error: () => {
				this.loadingResumen = false;
				// best-effort
			},
		});
	}

	cargarNotificaciones(): void {
		this.loadingNotificaciones = true;
		this.notificacionService.listar().subscribe({
			next: (data) => {
				this.notificaciones = data.items ?? [];
				this.unreadCount = Number(data.unread_count ?? 0);
				this.loadingNotificaciones = false;
			},
			error: (err) => {
				this.loadingNotificaciones = false;
				if (err?.status === 401 || err?.status === 422) {
					this.authService.logout();
					this.router.navigate(['/login']);
					return;
				}
				// notificaciones son opcionales en UI
			},
		});
	}

	marcarNotificacionLeida(n: Notificacion): void {
		if (!n || n.leida) return;
		this.notificacionService.marcarLeida(n.id).subscribe({
			next: () => {
				n.leida = true;
				this.unreadCount = Math.max(0, (this.unreadCount ?? 0) - 1);
			},
			error: () => {
				// best-effort
			},
		});
	}

	abrirNotificacion(n: Notificacion): void {
		const meta: any = (n as any)?.meta;
		const link = meta?.link;
		const chat = meta?.chat === true;
		const idRenta = meta?.id_renta ?? meta?.renta_id;

		if (link) {
			if (chat) {
				this.router.navigate([link], { queryParams: { chat: 1 }, fragment: 'chat' });
			} else {
				this.router.navigate([link]);
			}
			this.marcarNotificacionLeida(n);
			return;
		}

		if (idRenta) {
			this.router.navigate(['/rentas/resumen', idRenta]);
			this.marcarNotificacionLeida(n);
		}
	}

	tieneLink(n: Notificacion): boolean {
		const meta: any = (n as any)?.meta;
		return !!(meta?.link || meta?.id_renta || meta?.renta_id);
	}

	private titleCase(s: string): string {
		return String(s)
			.split(' ')
			.filter((p) => !!p)
			.map((p) => p.charAt(0).toUpperCase() + p.slice(1))
			.join(' ');
	}

	notiTitulo(n: Notificacion): string {
		const raw = String(n?.tipo ?? '').trim();
		if (!raw) return 'Notificación';
		return this.titleCase(raw.replace(/[_-]+/g, ' ').toLowerCase());
	}

	notiFecha(n: Notificacion): string {
		const raw = String(n?.created_at ?? '').trim();
		if (!raw) return '';
		const d = new Date(raw);
		if (Number.isNaN(d.getTime())) return raw;
		try {
			return d.toLocaleString('es-ES', {
				year: 'numeric',
				month: '2-digit',
				day: '2-digit',
				hour: '2-digit',
				minute: '2-digit',
			});
		} catch {
			return raw;
		}
	}

	private formatMonto(v: any): string | null {
		const n = typeof v === 'string' ? Number(v) : v;
		if (typeof n !== 'number' || !Number.isFinite(n)) return null;
		const fixed = Math.round(n) === n ? String(n) : n.toFixed(2);
		return `$${fixed}`;
	}

	notiExtra(n: Notificacion): string {
		const meta: any = (n as any)?.meta ?? {};
		const parts: string[] = [];

		const estado = meta?.estado_renta ?? meta?.estado;
		if (estado) parts.push(`Estado: ${String(estado)}`);

		const dep = this.formatMonto(meta?.monto_deposito);
		if (dep) parts.push(`Depósito: ${dep}`);

		const ret = this.formatMonto(meta?.monto_retenido);
		if (ret) parts.push(`Retenido: ${ret}`);

		const reem = this.formatMonto(meta?.monto_reembolso);
		if (reem) parts.push(`Reembolso: ${reem}`);

		if (meta?.chat === true) parts.push('Chat');

		const idRenta = meta?.id_renta ?? meta?.renta_id;
		if (idRenta) parts.push(`Renta #${idRenta}`);

		return parts.join(' · ');
	}

	cargarPerfil(): void {
		this.loadingUser = true;
		this.errorMessage = '';
		this.verificationMessage = '';
		this.profileMessage = '';

		this.authService.me().subscribe({
			next: (resp) => {
				this.user = resp.data;
				this.form.patchValue({
					nombre: this.user?.nombre ?? '',
					apellidos: this.user?.apellidos ?? '',
					telefono: this.user?.telefono ?? '',
					ciudad: this.user?.ciudad ?? '',
					estado: this.user?.estado ?? '',
					pais: this.user?.pais ?? '',
					direccion_completa: this.user?.direccion_completa ?? '',
				});
				this.rating = null;
				const id = Number(this.user?.id);
				if (Number.isFinite(id) && id > 0) {
					this.usuarioService.obtenerRating(id).subscribe({
						next: (r) => (this.rating = r),
						error: () => {
							// rating es opcional en UI
						},
					});
				}
				this.loadingUser = false;
			},
			error: (err) => {
				this.loadingUser = false;
				if (err?.status === 401 || err?.status === 422) {
					this.authService.logout();
					this.router.navigate(['/login']);
					return;
				}
				this.errorMessage = 'No se pudo cargar tu perfil.';
			},
		});
	}

	toggleEditar(): void {
		this.editMode = !this.editMode;
		this.profileMessage = '';
		this.errorMessage = '';
	}

	guardarPerfil(): void {
		this.profileMessage = '';
		this.errorMessage = '';
		if (this.form.invalid) {
			this.form.markAllAsTouched();
			this.errorMessage = 'Revisa los campos del perfil.';
			return;
		}

		this.savingProfile = true;
		const v = this.form.value;
		this.usuarioService
			.actualizarMe({
				nombre: String(v.nombre ?? '').trim() || null,
				apellidos: String(v.apellidos ?? '').trim() || null,
				telefono: String(v.telefono ?? '').trim() || null,
				ciudad: String(v.ciudad ?? '').trim() || null,
				estado: String(v.estado ?? '').trim() || null,
				pais: String(v.pais ?? '').trim() || null,
				direccion_completa: String(v.direccion_completa ?? '').trim() || null,
			})
			.subscribe({
				next: () => {
					this.savingProfile = false;
					this.profileMessage = 'Perfil actualizado.';
					this.editMode = false;
					this.cargarPerfil();
				},
				error: (err) => {
					this.savingProfile = false;
					if (err?.status === 401 || err?.status === 422) {
						this.authService.logout();
						this.router.navigate(['/login']);
						return;
					}
					this.errorMessage = err?.error?.message || 'No se pudo actualizar el perfil.';
				},
			});
	}

	enviarVerificacionCorreo(): void {
		this.verificationMessage = '';
		this.errorMessage = '';
		if (!this.user) return;

		this.sendingVerification = true;
		this.authService.enviarVerificacionEmail().subscribe({
			next: (resp) => {
				this.sendingVerification = false;
				this.verificationMessage = resp?.message || 'Link de verificación enviado.';
			},
			error: (err) => {
				this.sendingVerification = false;
				if (err?.status === 401 || err?.status === 422) {
					this.authService.logout();
					this.router.navigate(['/login']);
					return;
				}
				this.errorMessage = err?.error?.message || 'No se pudo enviar el link de verificación.';
			},
		});
	}

	cargarMisArticulos(): void {
		this.loadingArticulos = true;

		this.articuloService.misArticulos().subscribe({
			next: (arts) => {
				this.articulos = arts;
				this.loadingArticulos = false;
			},
			error: (err) => {
				this.loadingArticulos = false;
				if (err?.status === 401 || err?.status === 422) {
					this.authService.logout();
					this.router.navigate(['/login']);
					return;
				}
				this.errorMessage = 'No se pudieron cargar tus artículos.';
			},
		});
	}

	irAPublicar(): void {
		this.router.navigate(['/articulos/publicar']);
	}

	irADetalle(art: Articulo): void {
		this.router.navigate(['/articulos', art.id]);
	}

	irAEditar(art: Articulo): void {
		this.router.navigate(['/articulos/editar', art.id]);
	}

	irAExplorar(): void {
		this.router.navigate(['/explorar']);
	}

	cerrarSesion(): void {
		this.authService.logout();
		this.router.navigate(['/login']);
	}
}
