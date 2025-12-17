// src/app/app-routing.module.ts
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { LoginComponent } from './features/auth/login/login.component';
import { RegisterComponent } from './features/auth/register/register.component';
import { VerifyEmailComponent } from './features/auth/verify-email/verify-email.component';
import { HomeComponent } from './features/home/home.component';
import { ListadoArticulosComponent } from './features/articulos/listado/listado-articulos.component';
import { PublicarArticuloComponent } from './features/articulos/publicar/publicar-articulo.component';
import { EditarArticuloComponent } from './features/articulos/editar/editar-articulo.component';
import { PerfilComponent } from './features/usuarios/perfil/perfil.component';
import { DetalleArticuloComponent } from './features/articulos/detalle/detalle-articulo.component';
import { RentarArticuloComponent } from './features/rentas/rentar/rentar-articulo.component';
import { RentaResumenComponent } from './features/rentas/resumen/renta-resumen.component';
import { MisRentasComponent } from './features/rentas/mis/mis-rentas.component';
import { InboxComponent } from './features/rentas/inbox/inbox.component';
import { AuthGuard } from './core/guards/auth.guard';
import { RoleGuard } from './core/guards/role.guard';

import { DashboardComponent } from './features/admin/dashboard/dashboard.component';
import { AdminIncidentesComponent } from './features/admin/incidentes/admin-incidentes.component';
import { AdminUsuariosComponent } from './features/admin/usuarios/admin-usuarios.component';
import { AdminArticulosComponent } from './features/admin/articulos/admin-articulos.component';
import { AdminPuntosEntregaComponent } from './features/admin/puntos-entrega/admin-puntos-entrega.component';

const routes: Routes = [
  { path: '', component: HomeComponent, pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: 'verificar-email', component: VerifyEmailComponent },

  // Alias de navegación: “Explorar”
  { path: 'explorar', redirectTo: 'articulos/listado', pathMatch: 'full' },

  {
    path: 'articulos/listado',
    component: ListadoArticulosComponent,
  },

  {
    path: 'articulos/publicar',
    component: PublicarArticuloComponent,
    canActivate: [AuthGuard],
  },

  {
    path: 'articulos/editar/:id',
    component: EditarArticuloComponent,
    canActivate: [AuthGuard],
  },

  {
    path: 'perfil',
    component: PerfilComponent,
    canActivate: [AuthGuard],
  },

  {
    path: 'articulos/:id',
    component: DetalleArticuloComponent,
  },

  {
    path: 'rentas/crear/:id',
    component: RentarArticuloComponent,
    canActivate: [AuthGuard],
  },

  {
    path: 'rentas/resumen/:id',
    component: RentaResumenComponent,
    canActivate: [AuthGuard],
  },

  {
    path: 'rentas/mis',
    component: MisRentasComponent,
    canActivate: [AuthGuard],
  },

  {
    path: 'inbox',
    component: InboxComponent,
    canActivate: [AuthGuard],
  },

  // Panel Admin (protegido por rol)
  {
    path: 'admin',
    component: DashboardComponent,
    canActivate: [AuthGuard, RoleGuard],
    data: { roles: ['ADMIN'] },
  },
  {
    path: 'admin/incidentes',
    component: AdminIncidentesComponent,
    canActivate: [AuthGuard, RoleGuard],
    data: { roles: ['ADMIN'] },
  },
  {
    path: 'admin/usuarios',
    component: AdminUsuariosComponent,
    canActivate: [AuthGuard, RoleGuard],
    data: { roles: ['ADMIN'] },
  },
  {
    path: 'admin/articulos',
    component: AdminArticulosComponent,
    canActivate: [AuthGuard, RoleGuard],
    data: { roles: ['ADMIN'] },
  },
  {
    path: 'admin/puntos-entrega',
    component: AdminPuntosEntregaComponent,
    canActivate: [AuthGuard, RoleGuard],
    data: { roles: ['ADMIN'] },
  },

  { path: '**', redirectTo: '' },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
