# Research and direct-download route

Observed 15 September 2026. The target is Adobe **cloud Lightroom**, product
code LRCC, with a genuine subscription. Lightroom Classic uses a different code
and is not interchangeable evidence.

## Adobe's own distribution endpoints

Adobe's public catalog was fetched from:

`https://prod-rel-ffc-ccm.oobesaas.adobe.com/adobe-ffc-external/core/v6/products/all?channel=ccm&channel=sti&platform=win64&productType=Desktop&_type=xml`

Headers: `X-Adobe-App-Id: accc-hdcore-desktop`, `X-Api-Key: CC_HD_ESD_1_0`,
user agent `Adobe Application Manager 2.0`. These are catalog identifiers, not
user credentials. The endpoint was identified by reading the
[Adobe packager](https://github.com/ckamte/adobe-packager-windows) source;
its downloader was not executed.

For LRCC 9.5.1, the catalog build GUID is
`47c8669e-6e6b-4a1d-9b97-61c1e2427b43`. Passing it as `x-adobe-build-guid`
to `https://cdn-ffc.oobesaas.adobe.com/core/v3/applications` returned the
package URL pinned in manifest.json. The package server required user agent
`Creative Cloud`; ordinary curl received HTTP 403.

The downloaded ZIP contains Windows paths under `1\Adobe Lightroom\`.
Although ZIP entries are stored without ZIP compression, each payload has an
additional raw LZMA2 layer. Its first byte encodes the dictionary size using
the LZMA2 property formula. The launcher decodes these files and checks that
the resulting lightroom.exe has a Windows PE header. It leaves Adobe's binary
code and licensing intact. Installer registration is not fully reproduced.

Raw research responses, installer archives and logs are local-only and ignored
by Git. No account tokens or signed-in environment belong in this repository.

## Compatibility evidence

- [sander110419/lightroom-cc-on-linux](https://github.com/sander110419/lightroom-cc-on-linux)
  documents Lightroom CC 9.3.1 on Wine, with several API workarounds. The
  claimed workflow is not independent proof of reliability on this machine.
- [6im0n/lightroom-classic-on-linux](https://github.com/6im0n/lightroom-classic-on-linux)
  provides newer Arch/Intel findings and an inspectable Direct2D source patch.
- [PhialsBasement/wine-adobe-installers](https://github.com/PhialsBasement/wine-adobe-installers)
  supplies the isolated Adobe-compatible Wine runner used here.
- [Microsoft WebView2](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)
  provides the standalone browser runtime. Installing it locally cleared
  Lightroom's missing-WebView2 message.

Proton translates Windows APIs; it does not guarantee every Windows program
works. SteamOS combines open-source Linux components with proprietary Steam
software. We borrow per-app compatibility configuration from
[Proton](https://github.com/ValveSoftware/Proton), side-by-side runners from
[CachyOS](https://wiki.cachyos.org/configuration/gaming/), and convenient app
lifecycle management from [Bazzite](https://docs.bazzite.gg/Installing_and_Managing_Software/software-intro/).
None of those distributions supplies missing Adobe compatibility automatically.

The [Darling project](https://www.darlinghq.org/) is the relevant macOS API
compatibility effort. No Lightroom-on-Darling result was verified.

Grok CLI produced no substantive X findings. agy headless research was blocked
by its read_url permissions. Neither supplied usable YouTube transcript evidence.

## Bundled authentication browser

The direct Lightroom payload omits Adobe Desktop Common components. On the
local Proton test, NGL logged missing CEF workflow dependencies, then WebView2
controller initialization failure, then fallback to IE. The visible Adobe
"Update your browser" page was therefore the IE fallback, not proof that
Chromium rendered successfully.

The checksum-pinned Creative Cloud offline archive contains independently
extractable ADC64/CEF64 and ADC64/NGL .pima ZIP packages. Their .pimx metadata
places them in CEF and NGL under Adobe Desktop Common. Staging only those two
components provides Adobe's own authentication helper and Chromium engine
without installing the Creative Cloud desktop UI. The archive's CEF reports
Chrome/116.0.5845.190; current Adobe login acceptance remains to be tested.

A Wine Staging developer also reviewed the earlier Lightroom recipe:
https://www.patreon.com/winestaging/posts/investigation-of-160397129
The missing e26b366d COM class is RealTimeStylus, not an Adobe licensing class.
We have not installed the recipe's guessed COM stub or its mfplat binary patch.
