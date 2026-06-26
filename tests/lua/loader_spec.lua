-- Uso: lua tests/lua/loader_spec.lua  (HYPR_AJUSTES_DIR apunta al dir de prueba)
-- El runner de pytest prepara el dir y exporta HYPR_AJUSTES_DIR.
package.path = "lua/?/init.lua;" .. package.path
local settings = require("settings")

local failures = 0
local function check(name, ok)
    if not ok then
        failures = failures + 1
        io.stderr:write("FAIL: " .. name .. "\n")
    end
end

local defaults = { gaps = 8, blur = true }

-- archivo inexistente → defaults tal cual
local missing = settings.load("no_existe", defaults)
check("missing devuelve defaults", missing.gaps == 8 and missing.blur == true)

-- JSON válido → valores del archivo, claves ausentes rellenadas de defaults
local valid = settings.load("valido", defaults)
check("valido lee gaps", valid.gaps == 12)
check("valido completa blur desde defaults", valid.blur == true)
check("valido lee string", valid.nombre == "tendró ñ")
check("valido lee lista", #valid.lista == 3 and valid.lista[2] == 2)
check("valido lee anidado", valid.anidado.x == -1.5)
check("valido lee null como nil", valid.nulo == nil)

-- JSON corrupto → defaults, sin error
local corrupt = settings.load("corrupto", defaults)
check("corrupto devuelve defaults", corrupt.gaps == 8)

-- raíz no-objeto → defaults
local array_root = settings.load("raiz_lista", defaults)
check("raiz no objeto devuelve defaults", array_root.gaps == 8)

if failures > 0 then os.exit(1) end
print("OK")
