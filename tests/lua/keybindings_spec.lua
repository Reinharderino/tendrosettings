-- Uso: SPEC_CASE=mixed|vacio lua tests/lua/keybindings_spec.lua
-- El runner pytest prepara HYPR_AJUSTES_DIR con el keybindings.json del caso.
package.path = "lua/?/init.lua;" .. package.path
local settings = require("settings")

local failures = 0
local function check(name, ok)
    if not ok then
        failures = failures + 1
        io.stderr:write("FAIL: " .. name .. "\n")
    end
end

-- hl falso: cada hl.dsp.* devuelve una tabla-sentinela con lo que recibió,
-- y hl.bind registra las llamadas para inspeccionarlas.
local calls = {}
local function dsp(kind)
    return function(opts) return { kind = kind, opts = opts } end
end
local hl = {
    bind = function(combo, action) calls[#calls + 1] = { combo = combo, action = action } end,
    dsp = {
        exec_cmd = dsp("exec_cmd"),
        focus = dsp("focus"),
        window = {
            close = dsp("window.close"),
            fullscreen = dsp("window.fullscreen"),
            float = dsp("window.float"),
            move = dsp("window.move"),
        },
        workspace = { toggle_special = dsp("workspace.toggle_special") },
    },
}

local registered = settings.keybindings(hl)
local case = os.getenv("SPEC_CASE") or "mixed"

if case == "mixed" then
    check("registra solo los binds válidos y habilitados", registered == 4 and #calls == 4)
    check("combo con mods y key", calls[1].combo == "SUPER + SHIFT + B")
    check("exec usa hl.dsp.exec_cmd(comando)",
          calls[1].action.kind == "exec_cmd" and calls[1].action.opts == "firefox")
    check("goto_workspace usa focus({workspace=N}) numérico",
          calls[2].action.kind == "focus" and calls[2].action.opts.workspace == 3)
    check("focus_direction usa focus({direction=d})",
          calls[3].action.kind == "focus" and calls[3].action.opts.direction == "left")
    check("toggle_float usa window.float({action='toggle'})",
          calls[4].action.kind == "window.float" and calls[4].action.opts.action == "toggle")
else -- "vacio": JSON ausente o corrupto
    check("sin binds registrados", registered == 0 and #calls == 0)
end

if failures > 0 then os.exit(1) end
print("OK")
