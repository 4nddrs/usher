import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


def borrar_coleccion_completa():
    # 1. Inicializar la app de Firebase con tu archivo de credenciales
    try:
        cred = credentials.Certificate("key.json")
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✔ Conexión con Firebase establecida correctamente.")
    except Exception as e:
        print(f"❌ Error al conectar con Firebase: {e}")
        return

    # Definir la colección a borrar
    coleccion_nombre = "asignaciones"
    coleccion_ref = db.collection(coleccion_nombre)

    # Tamaño del lote para ir borrando poco a poco (Firebase recomienda máximo 500 por lote)
    tamano_lote = 100
    total_borrados = 0

    print(f"⌛ Iniciando el borrado de la colección '{coleccion_nombre}'...")

    while True:
        # Obtener un lote de documentos (solo necesitamos los IDs para borrarlos)
        docs = list(coleccion_ref.limit(tamano_lote).stream())

        # Si ya no hay documentos, salimos del bucle
        if not docs:
            break

        # Crear un "Write Batch" para borrar en grupo
        batch = db.batch()
        for doc in docs:
            batch.delete(doc.reference)

        # Comprometer/aplicar los cambios del lote
        batch.commit()

        total_borrados += len(docs)
        print(
            f"  -> Borrados {len(docs)} documentos en este lote... (Total: {total_borrados})"
        )

    print(
        f"\n✨ ¡Proceso terminado! Se borraron un total de {total_borrados} documentos de '{coleccion_nombre}'."
    )


if __name__ == "__main__":
    # Alerta de seguridad antes de ejecutar
    confirmacion = input(
        "⚠️ ¡ADVERTENCIA! Esto borrará TODOS los documentos de 'asignaciones'. ¿Continuar? (s/n): "
    )
    if confirmacion.lower() == "s":
        borrar_coleccion_completa()
    else:
        print("❌ Operación cancelada por el usuario.")
