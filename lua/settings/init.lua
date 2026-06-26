-- Loader de datos de hypr-ajustes.
-- hyprland.lua hace require("settings") y lee los JSON que escribe la app GTK.
-- La sesión NUNCA depende de JSON válido: archivo ausente o corrupto → defaults.

local M = {}

-- ---------- decoder JSON mínimo (objetos, listas, strings, números, bool, null) ----------
-- Embebido para no depender de librerías externas en el Lua de Hyprland.

local function decode_error(pos, msg)
    error(string.format("json: %s (byte %d)", msg, pos), 0)
end

local function skip_ws(s, pos)
    local next_pos = s:find("[^ \t\r\n]", pos)
    return next_pos or (#s + 1)
end

local ESCAPES = {
    ['"'] = '"', ["\\"] = "\\", ["/"] = "/",
    n = "\n", t = "\t", r = "\r", b = "\b", f = "\f",
}

local function codepoint_to_string(cp)
    if utf8 and utf8.char then return utf8.char(cp) end
    if cp < 128 then return string.char(cp) end
    return "?" -- Lua 5.1 sin utf8: degradación aceptable para settings
end

local function decode_string(s, pos) -- pos sobre la comilla inicial
    local parts = {}
    local i = pos + 1
    while i <= #s do
        local c = s:sub(i, i)
        if c == '"' then
            return table.concat(parts), i + 1
        elseif c == "\\" then
            local esc = s:sub(i + 1, i + 1)
            if ESCAPES[esc] then
                parts[#parts + 1] = ESCAPES[esc]
                i = i + 2
            elseif esc == "u" then
                local cp = tonumber(s:sub(i + 2, i + 5), 16)
                if not cp then decode_error(i, "escape \\u inválido") end
                parts[#parts + 1] = codepoint_to_string(cp)
                i = i + 6
            else
                decode_error(i, "escape inválido")
            end
        else
            parts[#parts + 1] = c
            i = i + 1
        end
    end
    decode_error(pos, "string sin cerrar")
end

local function decode_number(s, pos)
    local literal = s:match("^-?%d+%.?%d*[eE]?[-+]?%d*", pos)
    local value = literal and tonumber(literal)
    if not value then decode_error(pos, "número inválido") end
    return value, pos + #literal
end

local decode_value

local function decode_array(s, pos) -- pos sobre '['
    local out = {}
    pos = skip_ws(s, pos + 1)
    if s:sub(pos, pos) == "]" then return out, pos + 1 end
    while true do
        local value
        value, pos = decode_value(s, pos)
        out[#out + 1] = value
        pos = skip_ws(s, pos)
        local c = s:sub(pos, pos)
        if c == "]" then return out, pos + 1 end
        if c ~= "," then decode_error(pos, "se esperaba ',' o ']'") end
        pos = skip_ws(s, pos + 1)
    end
end

local function decode_object(s, pos) -- pos sobre '{'
    local out = {}
    pos = skip_ws(s, pos + 1)
    if s:sub(pos, pos) == "}" then return out, pos + 1 end
    while true do
        if s:sub(pos, pos) ~= '"' then decode_error(pos, "se esperaba clave string") end
        local key, value
        key, pos = decode_string(s, pos)
        pos = skip_ws(s, pos)
        if s:sub(pos, pos) ~= ":" then decode_error(pos, "se esperaba ':'") end
        value, pos = decode_value(s, skip_ws(s, pos + 1))
        out[key] = value
        pos = skip_ws(s, pos)
        local c = s:sub(pos, pos)
        if c == "}" then return out, pos + 1 end
        if c ~= "," then decode_error(pos, "se esperaba ',' o '}'") end
        pos = skip_ws(s, pos + 1)
    end
end

decode_value = function(s, pos)
    local c = s:sub(pos, pos)
    if c == "{" then return decode_object(s, pos) end
    if c == "[" then return decode_array(s, pos) end
    if c == '"' then return decode_string(s, pos) end
    if c == "t" and s:sub(pos, pos + 3) == "true" then return true, pos + 4 end
    if c == "f" and s:sub(pos, pos + 4) == "false" then return false, pos + 5 end
    if c == "n" and s:sub(pos, pos + 3) == "null" then return nil, pos + 4 end
    if c == "-" or c:match("%d") then return decode_number(s, pos) end
    decode_error(pos, "valor inesperado")
end

function M.decode(text)
    local value, pos = decode_value(text, skip_ws(text, 1))
    if skip_ws(text, pos) <= #text then decode_error(pos, "contenido extra tras el valor") end
    return value
end

-- ---------- API del loader ----------

local function settings_dir()
    return os.getenv("HYPR_AJUSTES_DIR")
        or (os.getenv("HOME") or "/nonexistent") .. "/.config/hypr/settings"
end

--- Carga <name>.json. Ausente/corrupto/no-objeto → defaults.
--- Claves ausentes en el JSON se completan (merge superficial) desde defaults.
function M.load(name, defaults)
    defaults = defaults or {}
    local file = io.open(settings_dir() .. "/" .. name .. ".json", "r")
    if not file then return defaults end
    local content = file:read("*a")
    file:close()
    local ok, value = pcall(M.decode, content)
    if not ok or type(value) ~= "table" or #value > 0 then return defaults end
    for key, default_value in pairs(defaults) do
        if value[key] == nil then value[key] = default_value end
    end
    return value
end

-- ---------- keybindings ----------
-- Lista blanca compartida con ajustes/core/keybindings.py (mantener en sintonía).
-- Formas hl.dsp validadas contra hyprland.lua real y los stubs hl.meta.lua.

local function keybinding_action(hl, action)
    if type(action) ~= "table" then return nil, "action no es objeto" end
    if action.type == "exec" then
        if type(action.command) ~= "string" or action.command == "" then
            return nil, "exec sin comando"
        end
        return hl.dsp.exec_cmd(action.command)
    end
    if action.type ~= "dispatcher" then
        return nil, "tipo desconocido: " .. tostring(action.type)
    end
    local name, arg = action.name, action.arg
    if name == "close_window" then return hl.dsp.window.close() end
    if name == "fullscreen" then return hl.dsp.window.fullscreen() end
    if name == "toggle_float" then return hl.dsp.window.float({ action = "toggle" }) end
    if name == "toggle_special" then return hl.dsp.workspace.toggle_special() end
    if name == "goto_workspace" or name == "move_to_workspace" then
        local n = tonumber(arg)
        if not n then return nil, tostring(name) .. " sin workspace numérico" end
        if name == "goto_workspace" then return hl.dsp.focus({ workspace = n }) end
        return hl.dsp.window.move({ workspace = n })
    end
    if name == "focus_direction" then
        if arg ~= "left" and arg ~= "right" and arg ~= "up" and arg ~= "down" then
            return nil, "dirección inválida: " .. tostring(arg)
        end
        return hl.dsp.focus({ direction = arg })
    end
    return nil, "dispatcher fuera de la lista blanca: " .. tostring(name)
end

local function keybinding_combo(bind)
    if type(bind.mods) ~= "table" or #bind.mods == 0 then return nil end
    if type(bind.key) ~= "string" or bind.key == "" then return nil end
    for _, mod in ipairs(bind.mods) do
        if type(mod) ~= "string" then return nil end
    end
    return table.concat(bind.mods, " + ") .. " + " .. bind.key
end

--- Registra los binds de keybindings.json con hl.bind. Devuelve cuántos registró.
--- JAMÁS lanza error: una entrada malformada se omite con aviso por stdout
--- (la sesión no puede depender de que el JSON sea válido).
function M.keybindings(hl)
    local data = M.load("keybindings", { binds = {} })
    local binds = type(data.binds) == "table" and data.binds or {}
    local registered = 0
    for index, bind in ipairs(binds) do
        if type(bind) == "table" and bind.enabled ~= false then
            local combo = keybinding_combo(bind)
            local action, why = keybinding_action(hl, bind.action)
            if combo and action then
                local ok, err = pcall(hl.bind, combo, action)
                if ok then
                    registered = registered + 1
                else
                    print("hypr-ajustes: bind '" .. combo .. "' omitido: " .. tostring(err))
                end
            else
                print("hypr-ajustes: keybindings.json#" .. index .. " omitido: "
                      .. (why or "combinación inválida"))
            end
        end
    end
    return registered
end

--- Aplica la configuración de monitores desde monitors.json con hl.monitor().
--- JAMÁS lanza error: JSON ausente o corrupto → no hace nada.
function M.monitors(hl)
    local data = M.load("monitors", { monitors = {}, power = {} })
    local list = type(data.monitors) == "table" and data.monitors or {}
    local registered = 0
    for _, spec in ipairs(list) do
        if type(spec) == "table" and type(spec.name) == "string" and spec.name ~= "" then
            local x = type(spec.x) == "number" and math.floor(spec.x) or 0
            local y = type(spec.y) == "number" and math.floor(spec.y) or 0
            local ok, err = pcall(hl.monitor, {
                output    = spec.name,
                mode      = type(spec.mode) == "string" and spec.mode or "preferred",
                position  = x .. " " .. y,
                scale     = type(spec.scale) == "number" and spec.scale or 1.0,
                transform = type(spec.transform) == "number" and spec.transform or 0,
                disabled  = spec.enabled == false,
            })
            if ok then
                registered = registered + 1
            else
                print("hypr-ajustes: monitor '" .. spec.name .. "' omitido: " .. tostring(err))
            end
        end
    end
    return registered
end

--- Aplica la apariencia (look & feel) desde appearance.json con hl.config.
--- Sobreescribe los defaults de hyprland.lua porque se llama después de ellos.
--- JAMÁS lanza error: JSON ausente o corrupto → no hace nada (quedan los defaults).
--- Devuelve 1 si aplicó, 0 si no.
function M.appearance(hl)
    local file = io.open(settings_dir() .. "/appearance.json", "r")
    if not file then return 0 end
    local content = file:read("*a")
    file:close()
    local ok, data = pcall(M.decode, content)
    if not ok or type(data) ~= "table" then return 0 end

    local function num(value, fallback)
        return type(value) == "number" and value or fallback
    end
    local function color(value, fallback)
        return type(value) == "string" and value ~= "" and value or fallback
    end

    local applied, err = pcall(hl.config, {
        general = {
            gaps_in     = num(data.gaps_in, 5),
            gaps_out    = num(data.gaps_out, 10),
            border_size = num(data.border_size, 2),
            col = {
                active_border = {
                    colors = {
                        color(data.active_color_1, "rgba(33ccffee)"),
                        color(data.active_color_2, "rgba(00ff99ee)"),
                    },
                    angle = num(data.gradient_angle, 45),
                },
                inactive_border = color(data.inactive_color, "rgba(595959aa)"),
            },
        },
        decoration = {
            rounding = num(data.rounding, 10),
            blur = {
                enabled = data.blur_enabled ~= false,
                size    = num(data.blur_size, 3),
                passes  = num(data.blur_passes, 1),
            },
        },
        animations = {
            enabled = data.animations_enabled ~= false,
        },
    })
    if not applied then
        print("hypr-ajustes: appearance omitido: " .. tostring(err))
        return 0
    end
    return 1
end

--- Aplica las animaciones individuales desde animations.json con hl.animation.
--- Sobreescribe los hl.animation de hyprland.lua porque se llama después.
--- JAMÁS lanza error: una entrada malformada se omite con aviso por stdout.
--- Devuelve cuántos leaves aplicó.
function M.animations(hl)
    local data = M.load("animations", { animations = {} })
    local list = type(data.animations) == "table" and data.animations or {}
    local applied = 0
    for _, leaf in ipairs(list) do
        if type(leaf) == "table" and type(leaf.name) == "string" and leaf.name ~= "" then
            local spec = {
                leaf    = leaf.name,
                enabled = leaf.enabled ~= false,
                speed   = type(leaf.speed) == "number" and leaf.speed or 7.0,
                bezier  = type(leaf.bezier) == "string" and leaf.bezier or "default",
            }
            if type(leaf.style) == "string" and leaf.style ~= "" then
                spec.style = leaf.style
            end
            local ok, err = pcall(hl.animation, spec)
            if ok then
                applied = applied + 1
            else
                print("hypr-ajustes: animación '" .. leaf.name .. "' omitida: " .. tostring(err))
            end
        end
    end
    return applied
end

-- ---------- wallpaper animado ----------
-- hyprpaper maneja los estáticos; swww/awww los animados, vía el script agnóstico
-- wallpaper-swww.sh. Aquí solo restauramos al iniciar sesión los monitores marcados
-- "animated" en wallpaper.json. JAMÁS lanza error: JSON ausente/corrupto → no hace nada.

local function shell_quote(value)
    -- Comilla simple POSIX: 'foo' con cada ' escapada como '\''.
    return "'" .. tostring(value):gsub("'", "'\\''") .. "'"
end

local ANIMATED_SCRIPT = (os.getenv("HOME") or "")
    .. "/.config/hypr/scripts/wallpaper-swww.sh"

--- Aplica con hl.exec_cmd el wallpaper animado de cada monitor marcado en
--- wallpaper.json. Devuelve cuántos aplicó. El script arranca el daemon solo.
function M.wallpaper(hl)
    local data = M.load("wallpaper", { monitors = {} })
    local monitors = type(data.monitors) == "table" and data.monitors or {}
    local applied = 0
    for name, spec in pairs(monitors) do
        if type(name) == "string" and name ~= ""
            and type(spec) == "table" and spec.animated == true
            and type(spec.path) == "string" and spec.path ~= ""
        then
            local fit = type(spec.fit_mode) == "string" and spec.fit_mode or "cover"
            local cmd = table.concat({
                shell_quote(ANIMATED_SCRIPT),
                "--output", shell_quote(name),
                "--fit", shell_quote(fit),
                shell_quote(spec.path),
            }, " ")
            local ok, err = pcall(hl.exec_cmd, cmd)
            if ok then
                applied = applied + 1
            else
                print("hypr-ajustes: wallpaper '" .. name .. "' omitido: " .. tostring(err))
            end
        end
    end
    return applied
end

return M
