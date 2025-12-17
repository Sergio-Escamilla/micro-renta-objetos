import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from 'src/app/core/services/auth.service';

@Component({
  selector: 'app-verify-email',
  templateUrl: './verify-email.component.html',
  styleUrls: ['./verify-email.component.scss'],
})
export class VerifyEmailComponent implements OnInit {
  loading = true;
  success = false;
  message = '';

  constructor(
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly authService: AuthService
  ) {}

  ngOnInit(): void {
    const token = String(this.route.snapshot.queryParamMap.get('token') || '').trim();
    if (!token) {
      this.loading = false;
      this.success = false;
      this.message = 'Falta el token de verificación.';
      return;
    }

    this.authService.verificarEmail(token).subscribe({
      next: () => {
        this.loading = false;
        this.success = true;
        this.message = 'Correo verificado correctamente.';
      },
      error: (err) => {
        this.loading = false;
        this.success = false;
        this.message = err?.error?.message || 'No se pudo verificar el correo.';
      },
    });
  }

  irALogin(): void {
    this.router.navigate(['/login']);
  }

  irAPerfil(): void {
    this.router.navigate(['/perfil']);
  }

  irAInicio(): void {
    this.router.navigate(['/']);
  }
}
