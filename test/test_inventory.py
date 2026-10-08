"""
test_inventory.py
=================
Pruebas unitarias para src/core/inventory.py

Ejecutar:
    python -m unittest tests.test_inventory -v
"""

import unittest

from src.core.warehouse import Position
from src.core.inventory import (
    Product,
    HashTable,
    InventoryManager,
)


# ---------------------------------------------------------------------------
# 1. Product
# ---------------------------------------------------------------------------
class TestProduct(unittest.TestCase):

    def test_creacion_basica(self):
        p = Product("P001", "Tornillo", Position(1, 2, 3), 20)
        self.assertEqual(p.product_id, "P001")
        self.assertEqual(p.name, "Tornillo")
        self.assertEqual(p.location, Position(1, 2, 3))
        self.assertEqual(p.stock, 20)

    def test_stock_por_defecto_cero(self):
        p = Product("P001", "Tornillo", Position(0, 0, 0))
        self.assertEqual(p.stock, 0)

    def test_product_id_vacio_lanza_error(self):
        with self.assertRaises(ValueError):
            Product("", "X", Position(0, 0, 0))

    def test_stock_negativo_lanza_error(self):
        with self.assertRaises(ValueError):
            Product("P001", "X", Position(0, 0, 0), -1)

    def test_round_trip_dict(self):
        p1 = Product("P001", "Tornillo", Position(1, 2, 3), 20)
        d = p1.to_dict()
        p2 = Product.from_dict(d)
        self.assertEqual(p1.product_id, p2.product_id)
        self.assertEqual(p1.name, p2.name)
        self.assertEqual(p1.location, p2.location)
        self.assertEqual(p1.stock, p2.stock)


# ---------------------------------------------------------------------------
# 2. HashTable — operaciones básicas
# ---------------------------------------------------------------------------
class TestHashTableBasico(unittest.TestCase):

    def setUp(self):
        self.ht = HashTable(capacity=8)

    def test_tabla_vacia(self):
        self.assertEqual(len(self.ht), 0)
        self.assertEqual(self.ht.load_factor(), 0.0)

    def test_insert_y_search(self):
        self.ht.insert("k1", "v1")
        self.assertEqual(self.ht.search("k1"), "v1")
        self.assertEqual(len(self.ht), 1)

    def test_search_inexistente_lanza_keyerror(self):
        with self.assertRaises(KeyError):
            self.ht.search("no_existe")

    def test_get_devuelve_default(self):
        self.assertIsNone(self.ht.get("no_existe"))
        self.assertEqual(self.ht.get("no_existe", "fallback"), "fallback")

    def test_insert_actualiza_si_clave_repetida(self):
        self.ht.insert("k1", "v1")
        self.ht.insert("k1", "v2")
        self.assertEqual(self.ht.search("k1"), "v2")
        self.assertEqual(len(self.ht), 1)   # no duplica

    def test_contains(self):
        self.ht.insert("k1", "v1")
        self.assertTrue(self.ht.contains("k1"))
        self.assertFalse(self.ht.contains("k2"))
        self.assertIn("k1", self.ht)
        self.assertNotIn("k2", self.ht)

    def test_delete(self):
        self.ht.insert("k1", "v1")
        self.ht.insert("k2", "v2")
        self.ht.delete("k1")
        self.assertFalse(self.ht.contains("k1"))
        self.assertTrue(self.ht.contains("k2"))
        self.assertEqual(len(self.ht), 1)

    def test_delete_inexistente_lanza_keyerror(self):
        with self.assertRaises(KeyError):
            self.ht.delete("no_existe")

    def test_delete_en_medio_de_cadena(self):
        """
        Si hay colisión, borrar un nodo intermedio no debe romper la cadena.
        Forzamos colisión usando la misma capacidad mínima.
        """
        ht = HashTable(capacity=8)
        # Insertamos varias claves; algunas colisionarán naturalmente
        for i in range(20):
            ht.insert("k%d" % i, "v%d" % i)
        for i in range(0, 20, 2):
            ht.delete("k%d" % i)
        for i in range(0, 20, 2):
            self.assertFalse(ht.contains("k%d" % i))
        for i in range(1, 20, 2):
            self.assertEqual(ht.search("k%d" % i), "v%d" % i)


# ---------------------------------------------------------------------------
# 3. HashTable — dunders
# ---------------------------------------------------------------------------
class TestHashTableDunders(unittest.TestCase):

    def setUp(self):
        self.ht = HashTable()

    def test_setitem_getitem(self):
        self.ht["a"] = 1
        self.assertEqual(self.ht["a"], 1)

    def test_delitem(self):
        self.ht["a"] = 1
        del self.ht["a"]
        self.assertNotIn("a", self.ht)

    def test_len(self):
        for i in range(5):
            self.ht[i] = i
        self.assertEqual(len(self.ht), 5)


# ---------------------------------------------------------------------------
# 4. HashTable — colisiones (clave de la Unidad 3)
# ---------------------------------------------------------------------------
class TestHashTableColisiones(unittest.TestCase):

    def test_colisiones_forzadas_cadena_correcta(self):
        """
        Forzamos colisiones usando una capacidad chica (8) e insertando
        muchas claves.  Todas deben recuperarse correctamente.
        """
        ht = HashTable(capacity=8)
        N = 100
        for i in range(N):
            ht.insert("clave_%d" % i, i * 10)

        self.assertEqual(len(ht), N)
        for i in range(N):
            self.assertEqual(ht.search("clave_%d" % i), i * 10)

    def test_actualizacion_bajo_colision(self):
        """Si dos claves colisionan, actualizar una no debe afectar la otra."""
        ht = HashTable(capacity=8)
        ht.insert("a", 1)
        ht.insert("b", 2)
        ht.insert("a", 100)   # actualización
        self.assertEqual(ht.search("a"), 100)
        self.assertEqual(ht.search("b"), 2)
        self.assertEqual(len(ht), 2)

    def test_borrado_bajo_colision_preserva_resto(self):
        ht = HashTable(capacity=8)
        N = 50
        for i in range(N):
            ht.insert("k%d" % i, i)
        # Borramos todas las pares
        for i in range(0, N, 2):
            ht.delete("k%d" % i)
        # Las impares deben seguir accesibles
        for i in range(1, N, 2):
            self.assertEqual(ht.search("k%d" % i), i)


# ---------------------------------------------------------------------------
# 5. HashTable — factor de carga y rehash
# ---------------------------------------------------------------------------
class TestHashTableRehash(unittest.TestCase):

    def test_rehash_duplica_capacidad(self):
        ht = HashTable(capacity=8)
        cap_inicial = ht._capacity

        # Insertamos hasta superar el umbral 0.75 -> 6 elementos
        for i in range(7):
            ht.insert("k%d" % i, i)

        self.assertGreater(ht._capacity, cap_inicial)
        # Los datos deben sobrevivir al rehash
        for i in range(7):
            self.assertEqual(ht.search("k%d" % i), i)

    def test_factor_de_carga_se_mantiene_bajo(self):
        ht = HashTable(capacity=8)
        for i in range(1000):
            ht.insert("k%d" % i, i)
        # Después de todos los rehashes, α debe ser <= 0.75
        self.assertLessEqual(ht.load_factor(), HashTable.LOAD_FACTOR_THRESHOLD)

    def test_rehash_no_pierde_datos(self):
        ht = HashTable(capacity=8)
        N = 500
        for i in range(N):
            ht.insert("clave%d" % i, i)
        self.assertEqual(len(ht), N)
        for i in range(N):
            self.assertEqual(ht.search("clave%d" % i), i)


# ---------------------------------------------------------------------------
# 6. HashTable — iteradores
# ---------------------------------------------------------------------------
class TestHashTableIteradores(unittest.TestCase):

    def setUp(self):
        self.ht = HashTable()
        self.pares = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}
        for k, v in self.pares.items():
            self.ht.insert(k, v)

    def test_keys(self):
        self.assertEqual(set(self.ht.keys()), set(self.pares.keys()))

    def test_values(self):
        self.assertEqual(set(self.ht.values()), set(self.pares.values()))

    def test_items(self):
        self.assertEqual(dict(self.ht.items()), self.pares)

    def test_iteradores_con_tabla_vacia(self):
        ht = HashTable()
        self.assertEqual(list(ht.keys()), [])
        self.assertEqual(list(ht.values()), [])
        self.assertEqual(list(ht.items()), [])


# ---------------------------------------------------------------------------
# 7. InventoryManager — CRUD
# ---------------------------------------------------------------------------
class TestInventoryManagerCRUD(unittest.TestCase):

    def setUp(self):
        self.inv = InventoryManager()
        self.p1 = Product("P001", "Tornillo", Position(0, 0, 0), 20)
        self.p2 = Product("P002", "Tuerca",   Position(5, 0, 0), 15)
        self.p3 = Product("P003", "Arandela", Position(10, 0, 0), 30)

    def test_add_y_get(self):
        self.inv.add_product(self.p1)
        self.assertEqual(self.inv.get_product("P001"), self.p1)

    def test_get_inexistente_lanza_keyerror(self):
        with self.assertRaises(KeyError):
            self.inv.get_product("NOEXISTE")

    def test_has_product(self):
        self.inv.add_product(self.p1)
        self.assertTrue(self.inv.has_product("P001"))
        self.assertFalse(self.inv.has_product("P999"))
        self.assertIn("P001", self.inv)
        self.assertNotIn("P999", self.inv)

    def test_remove_product(self):
        self.inv.add_product(self.p1)
        self.inv.remove_product("P001")
        self.assertFalse(self.inv.has_product("P001"))

    def test_len(self):
        self.assertEqual(len(self.inv), 0)
        self.inv.add_product(self.p1)
        self.inv.add_product(self.p2)
        self.assertEqual(len(self.inv), 2)

    def test_add_reemplaza_producto_con_mismo_id(self):
        self.inv.add_product(self.p1)
        p1_nuevo = Product("P001", "Tornillo v2", Position(0, 0, 0), 99)
        self.inv.add_product(p1_nuevo)
        self.assertEqual(len(self.inv), 1)
        self.assertEqual(self.inv.get_product("P001").name, "Tornillo v2")
        self.assertEqual(self.inv.get_product("P001").stock, 99)


# ---------------------------------------------------------------------------
# 8. InventoryManager — stock
# ---------------------------------------------------------------------------
class TestInventoryManagerStock(unittest.TestCase):

    def setUp(self):
        self.inv = InventoryManager()
        self.p1 = Product("P001", "Tornillo", Position(0, 0, 0), 20)
        self.inv.add_product(self.p1)

    def test_update_stock_positivo(self):
        nuevo = self.inv.update_stock("P001", 5)
        self.assertEqual(nuevo, 25)
        self.assertEqual(self.inv.get_product("P001").stock, 25)

    def test_update_stock_negativo(self):
        nuevo = self.inv.update_stock("P001", -3)
        self.assertEqual(nuevo, 17)

    def test_update_stock_a_cero(self):
        nuevo = self.inv.update_stock("P001", -20)
        self.assertEqual(nuevo, 0)

    def test_update_stock_negativo_invalido(self):
        with self.assertRaises(ValueError):
            self.inv.update_stock("P001", -100)

    def test_reserve_stock_exitoso(self):
        ok = self.inv.reserve_stock("P001", 5)
        self.assertTrue(ok)
        self.assertEqual(self.inv.get_product("P001").stock, 15)

    def test_reserve_stock_insuficiente(self):
        ok = self.inv.reserve_stock("P001", 100)
        self.assertFalse(ok)
        self.assertEqual(self.inv.get_product("P001").stock, 20)   # no cambia

    def test_reserve_stock_exacto(self):
        ok = self.inv.reserve_stock("P001", 20)
        self.assertTrue(ok)
        self.assertEqual(self.inv.get_product("P001").stock, 0)

    def test_reserve_cantidad_negativa_lanza_error(self):
        with self.assertRaises(ValueError):
            self.inv.reserve_stock("P001", -1)

    def test_get_location(self):
        loc = self.inv.get_location("P001")
        self.assertEqual(loc, Position(0, 0, 0))


# ---------------------------------------------------------------------------
# 9. InventoryManager — serialización
# ---------------------------------------------------------------------------
class TestInventorySerialization(unittest.TestCase):

    def test_round_trip(self):
        inv1 = InventoryManager()
        inv1.add_product(Product("P001", "A", Position(0, 0, 0), 10))
        inv1.add_product(Product("P002", "B", Position(5, 5, 5), 20))

        d = inv1.to_dict()
        inv2 = InventoryManager.from_dict(d)

        self.assertEqual(len(inv1), len(inv2))
        for pid in ["P001", "P002"]:
            p1 = inv1.get_product(pid)
            p2 = inv2.get_product(pid)
            self.assertEqual(p1.product_id, p2.product_id)
            self.assertEqual(p1.name, p2.name)
            self.assertEqual(p1.location, p2.location)
            self.assertEqual(p1.stock, p2.stock)


# ---------------------------------------------------------------------------
# 10. Escalabilidad
# ---------------------------------------------------------------------------
class TestInventoryEscalabilidad(unittest.TestCase):

    def test_muchos_productos(self):
        """Insertar 5000 productos y recuperarlos todos."""
        inv = InventoryManager()
        N = 5000
        for i in range(N):
            inv.add_product(Product(
                "P%05d" % i, "Prod %d" % i,
                Position(i % 100, i // 100, 0), 10
            ))
        self.assertEqual(len(inv), N)
        for i in range(0, N, 137):   # muestreo
            p = inv.get_product("P%05d" % i)
            self.assertEqual(p.name, "Prod %d" % i)


if __name__ == "__main__":
    unittest.main(verbosity=2)