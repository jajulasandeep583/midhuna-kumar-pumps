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
// Registers form handlers for Service Request and Kumar Warranty Claim. It lives
// in the shared bundle rather than doctype_js because it covers two doctypes that
// already have a script of their own, and its handlers simply never fire
// anywhere else.
import "./dealer_reply.js";
// The chat panel on the Service Request / Warranty Claim form. Same two
// doctypes, same reason for living in the shared bundle.
import "./dealer_chat.js";
