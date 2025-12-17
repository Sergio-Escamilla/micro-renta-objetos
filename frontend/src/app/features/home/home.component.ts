import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from 'src/app/core/services/auth.service';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent {
  constructor(private readonly authService: AuthService, private readonly router: Router) {}

  get isLoggedIn(): boolean {
    return this.authService.isAuthenticated();
  }

  irALogin(): void {
    this.router.navigate(['/login']);
  }

  irARegistro(): void {
    this.router.navigate(['/register']);
  }

  irAExplorar(): void {
    this.router.navigate(['/explorar']);
  }
}
