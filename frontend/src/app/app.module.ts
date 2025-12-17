// src/app/app.module.ts
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';

import { AuthModule } from './features/auth/auth.module';
import { HomeModule } from './features/home/home.module';
import { ArticulosModule } from './features/articulos/articulos.module';
import { UsuariosModule } from './features/usuarios/usuarios.module';
import { RentasModule } from './features/rentas/rentas.module';
import { AdminModule } from './features/admin/admin.module';
import { AuthInterceptor } from './core/interceptors/auth.interceptor';

@NgModule({
  declarations: [AppComponent],
  imports: [
    BrowserModule,
    HttpClientModule,
    AuthModule,
    HomeModule,
    ArticulosModule,
    UsuariosModule,
    RentasModule,
    AdminModule,
    AppRoutingModule,
  ],
  providers: [
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true,
    },
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
