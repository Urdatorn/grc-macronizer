local export = {}

function export.quote(text)
	return "“" .. text .. "”"
end

local function check_track_arg(argI, arg)
	require('libraryUtil').checkType("track", argI, arg, "string")
end

function export.track(template, code)
	check_track_arg(1, template)
	if code then
		check_track_arg(2, code)
		require('debug').track(template .. "/" .. code)
	else
		return function(code)
			check_track_arg(1, code)
			require('debug').track(template .. "/" .. code)
		end
	end
end

return export