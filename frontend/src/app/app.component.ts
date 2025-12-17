import { Component, OnDestroy, OnInit } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { AuthService } from './core/services/auth.service';
import { BadgeService } from './core/services/badge.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements OnInit, OnDestroy {
  badgeCount = 0;
  mobileMenuOpen = false;
  esAuthScreen = false;
  private sub: Subscription | null = null;
  private routeSub: Subscription | null = null;

  constructor(
    public readonly authService: AuthService,
    private readonly badgeService: BadgeService,
    private readonly router: Router
  ) {}

  ngOnInit(): void {
    this.iniciarBadgePolling();
    this.iniciarRouteWatcher();
  }

  ngOnDestroy(): void {
    if (this.sub) {
      this.sub.unsubscribe();
      this.sub = null;
    }

    if (this.routeSub) {
      this.routeSub.unsubscribe();
      this.routeSub = null;
    }

		this.badgeService.stopPolling();
  }

  private iniciarRouteWatcher(): void {
    if (this.routeSub) return;
    const compute = (url: string) => {
      const path = (url || '').split('?')[0].split('#')[0];
      return path === '/login' || path === '/register';
    };

    this.esAuthScreen = compute(this.router.url);
    this.routeSub = this.router.events.subscribe((ev) => {
      if (ev instanceof NavigationEnd) {
        this.esAuthScreen = compute(ev.urlAfterRedirects || ev.url);
      }
    });
  }

  private iniciarBadgePolling(): void {
    if (this.sub) return;

		this.badgeService.startPolling();
		this.sub = this.badgeService.badgeCount$.subscribe({
			next: (total) => (this.badgeCount = Number(total ?? 0) || 0),
			error: () => {
				// silencioso
			},
		});
  }

  irInbox(): void {
    this.router.navigate(['/inbox']);
  }

  irAExplorar(): void {
    this.router.navigate(['/explorar']);
  }

  irPerfil(): void {
    this.router.navigate(['/perfil']);
  }

  get esAdmin(): boolean {
    const roles = this.authService.getRoles();
    return (roles || []).some((r) => String(r).toUpperCase() === 'ADMIN' || String(r).toUpperCase() === 'ADMINISTRADOR');
  }

  toggleMobileMenu(): void {
    this.mobileMenuOpen = !this.mobileMenuOpen;
  }

  cerrarMobileMenu(): void {
    this.mobileMenuOpen = false;
  }
}
