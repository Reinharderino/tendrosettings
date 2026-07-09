-- Uso: SPEC_CASE=valid|skip_disabled|empty lua tests/lua/autostart_spec.lua
package.path = "lua/?/init.lua;" .. package.path
local settings = require("settings")

local failures = 0
local function check(name, ok)
    if not ok then
        failures = failures + 1
        io.stderr:write("FAIL: " .. name .. "\n")
    end
end

local exec_calls = {}
local hl = {
    exec_cmd = function(cmd) exec_calls[#exec_calls + 1] = cmd end,
}

local launched = settings.autostart(hl)
local case = os.getenv("SPEC_CASE") or "valid"

if case == "valid" then
    check("lanza 2 comandos", launched == 2 and #exec_calls == 2)
    check("primer comando", exec_calls[1] == "vesktop")
    check("segundo comando", exec_calls[2] == "telegram")
elseif case == "skip_disabled" then
    check("salta el disabled", launched == 1 and #exec_calls == 1)
    check("solo el enabled", exec_calls[1] == "vesktop")
elseif case == "empty" then
    check("sin comandos", launched == 0 and #exec_calls == 0)
else
    io.stderr:write("SPEC_CASE desconocido: " .. case .. "\n")
    os.exit(1)
end

if failures == 0 then print("OK") else os.exit(1) end
