
// frontend/src/app/core/models/articulo.model.ts
export interface Articulo {
  id: number;
  id_articulo?: number;
  titulo: string;
  precio_base?: number | null;
  precio_renta_dia?: number | null;
  precio_renta_hora?: number | null;
  deposito_garantia: number;
  unidad_precio?: 'por_hora' | 'por_dia' | 'por_semana' | string;
  estado: string;

  ciudad?: string | null;
  ubicacion_texto?: string | null;
  descripcion?: string | null;
  id_propietario?: number | null;

  imagenes?: Array<{
    id?: number;
    url_imagen: string;
    es_principal: boolean;
    orden?: number | null;
  }>;

  propietario_nombre: string | null;
  propietario_correo: string | null;
  imagen_principal_url: string | null;
}
