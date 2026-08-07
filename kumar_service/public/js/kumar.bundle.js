// Entry point for the desk bundle.
//
// These two files used to be listed in app_include_js by raw /assets path.
// Raw asset paths carry no content hash, so browsers cached them for the full
// 12-hour max-age and kept running old code after a deploy - the management
// screens rendered unstyled because the browser was holding a kumar.css from
// before the .kd-* rules existed. Going through the bundler gets each build a
// fresh hashed filename, so a deploy invalidates the cache by construction.
import "./kumar_common.js";
import "./kumar_dashboard.js";
