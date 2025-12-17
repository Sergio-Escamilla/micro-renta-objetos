export type ModalidadRenta = 'horas' | 'dias';

export interface RentaResumen {
	id: number;
	id_renta?: number;

	id_articulo: number;
	id_arrendatario: number;
	id_propietario: number;

	fecha_inicio: string;
	fecha_fin: string;

	modalidad?: ModalidadRenta;
	cantidad_unidades?: number | null;

	precio_total_renta: number;
	monto_deposito: number;
	subtotal_renta?: number;
	total_a_pagar?: number;
	estado_renta: string;

	reembolso_simulado?: boolean;
	monto_reembolso?: number;

	// Coordinación / privacidad
	modo_entrega?: 'arrendador' | 'neutral' | string | null;
	// Modo de entrega (domicilio vs punto seguro)
	entrega_modo?: 'domicilio' | 'punto_entrega' | string | null;
	punto_entrega?: {
		id: number;
		nombre: string;
		direccion?: string | null;
	} | null;
	zona_publica?: string | null;
	direccion_entrega_visible?: boolean;
	direccion_entrega?: string | null;
	ventanas_entrega_propuestas?: string[];
	ventana_entrega_elegida?: string | null;
	ventanas_devolucion_propuestas?: string[];
	ventana_devolucion_elegida?: string | null;
	coordinacion_confirmada?: boolean;

	// OTP
	codigo_entrega?: string | null;
	codigo_devolucion?: string | null;
	checklist_entrega?: string | null;
	checklist_devolucion?: string | null;

	// Chat
	chat_habilitado?: boolean;

	entregado?: boolean;
	devuelto?: boolean;
	deposito_liberado?: boolean;

	// Timeline (cuando el backend lo exponga; compat: opcional)
	timeline?: { [k: string]: string | null };
	fecha_pago?: string | null;
	fecha_coordinacion_confirmada?: string | null;
	fecha_entrega_confirmada?: string | null;
	fecha_en_uso?: string | null;
	fecha_finalizacion?: string | null;
	fecha_incidente?: string | null;
	fecha_cancelacion?: string | null;
	fecha_expiracion?: string | null;

	fecha_entrega?: string | null;
	fecha_devolucion?: string | null;
	fecha_liberacion_deposito?: string | null;

	notas_entrega?: string | null;
	notas_devolucion?: string | null;

	incidente?: {
		id: number;
		descripcion: string;
		decision?: 'liberar' | 'retener_parcial' | 'retener_total' | null;
		monto_retenido?: number | null;
		nota?: string | null;
		created_at?: string | null;
		resolved_at?: string | null;
	} | null;

	articulo?: {
		id?: number;
		id_articulo: number;
		titulo: string;
		precio_base?: number;
		precio_renta_dia?: number;
		unidad_precio?: string;
		monto_deposito?: number;
		deposito_garantia?: number;
		ubicacion_texto?: string | null;
	} | null;
}

