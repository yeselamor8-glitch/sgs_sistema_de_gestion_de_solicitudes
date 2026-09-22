"""
Reset completo de la base de datos:
1. Limpia el esquema
2. Recrea las tablas desde schema.sql
3. Ejecuta el seed inicial
"""
import sys

# Blindaje para Windows: algunas consolas (PowerShell con code page
# cp1252) truenan con UnicodeEncodeError si imprime emojis/acentos.
# Forzamos UTF-8 en la salida (mismo guard que seed_inicial.py).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, '.')

from sgs.config.db import engine
from sqlalchemy import text


def limpiar_esquema():
    print("1. Limpiando esquema...")
    with engine.connect() as conn:
        conn.execute(text('DROP SCHEMA public CASCADE'))
        conn.execute(text('CREATE SCHEMA public'))
        conn.commit()
    print("   ✅ Esquema limpio")


def recrear_tablas():
    print("2. Recreando tablas desde schema.sql...")
    with open('schema.sql', 'r', encoding='utf-8') as f:
        schema = f.read()

    # Limpiar comentarios línea por línea
    lineas = []
    for linea in schema.split('\n'):
        if '--' in linea:
            linea = linea[:linea.index('--')]
        lineas.append(linea)
    schema_limpio = '\n'.join(lineas)

    statements = [s.strip() for s in schema_limpio.split(';') if s.strip()]

    with engine.connect() as conn:
        ejecutados = 0
        errores = 0
        for stmt in statements:
            try:
                conn.execute(text(stmt))
                ejecutados += 1
            except Exception as e:
                if 'already exists' not in str(e).lower():
                    errores += 1
                    print(f"   ⚠️ {str(e)[:80]}")
        conn.commit()
    print(f"   ✅ {ejecutados} statements ejecutados, {errores} errores")


def ejecutar_seed():
    print("3. Ejecutando seed inicial...")
    from scripts.seed_inicial import main
    main()


def main():
    print("=" * 50)
    print("RESET COMPLETO DE BASE DE DATOS")
    print("=" * 50)
    limpiar_esquema()
    recrear_tablas()
    ejecutar_seed()
    print("=" * 50)
    print("✅ RESET COMPLETO")
    print("=" * 50)
    print("\nAhora puedes ejecutar:")
    print("  py -m sgs.ui.main")
    print("\nLogin:")
    print("  Usuario: admin")
    print("  Contraseña: CambiarEsta123")


if __name__ == '__main__':
    main()