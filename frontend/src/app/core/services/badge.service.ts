import { Injectable } from '@angular/core';
import { BehaviorSubject, Subscription, catchError, interval, map, of, startWith, switchMap, tap } from 'rxjs';
import { AuthService } from './auth.service';
import { NotificacionService } from './notificacion.service';
import { RentaService } from './renta.service';

@Injectable({ providedIn: 'root' })
export class BadgeService {
  private readonly badgeCountSubject = new BehaviorSubject<number>(0);
  readonly badgeCount$ = this.badgeCountSubject.asObservable();

  private pollingSub: Subscription | null = null;

  constructor(
    private readonly authService: AuthService,
    private readonly rentaService: RentaService,
    private readonly notificacionService: NotificacionService
  ) {}

  startPolling(): void {
    if (this.pollingSub) return;

    this.pollingSub = interval(15000)
      .pipe(
        startWith(0),
        switchMap(() => this.fetchBadgeTotal())
      )
      .subscribe({
        next: (total) => this.badgeCountSubject.next(total),
        error: () => {
          // silencioso
        },
      });
  }

  stopPolling(): void {
    if (!this.pollingSub) return;
    this.pollingSub.unsubscribe();
    this.pollingSub = null;
  }

  refreshOnce(): void {
    this.fetchBadgeTotal().subscribe({
      next: (total) => this.badgeCountSubject.next(total),
      error: () => {
        // best-effort
      },
    });
  }

  private fetchBadgeTotal() {
    if (!this.authService.isAuthenticated()) {
      return of(0);
    }

    return this.rentaService.chatUnreadTotal().pipe(
      catchError(() =>
        this.notificacionService.listar().pipe(
          map((d) => Number(d?.unread_count ?? 0) || 0),
          catchError(() => of(0))
        )
      ),
      map((n) => Number(n ?? 0) || 0)
    );
  }
}
