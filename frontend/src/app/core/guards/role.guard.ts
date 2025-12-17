import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, Router, RouterStateSnapshot } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Injectable({
	providedIn: 'root',
})
export class RoleGuard implements CanActivate {
	constructor(private readonly authService: AuthService, private readonly router: Router) {}

	canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): boolean {
		const required = (route.data?.['roles'] as string[] | undefined) ?? [];

		const roles = this.authService.getRoles().map((r) => String(r).toUpperCase());
		const isAdmin = roles.includes('ADMIN') || roles.includes('ADMINISTRADOR');

		// Por ahora el panel solo se usa para admin
		const needsAdmin = required.length === 0 || required.some((r) => String(r).toUpperCase() === 'ADMIN');
		if (needsAdmin && isAdmin) return true;

		// Si no tiene rol, lo mandamos a explorar (sin crear nuevas pantallas)
		this.router.navigate(['/explorar']);
		return false;
	}
}
