# LibTV「运镜」预设全集（cameraControl / config id=186）

> 来源：`https://api2.liblib.art/api/www/landing-activities/getById?id=186`
> 抓取：2026-09-23。机制 = 选中项的 `prompt` 片段**追加到提示词尾部**（片段自带前导 `, `）。
> 参数落点：节点 `data.params.cameraControl`（选择项）+ `data.params.cameraPresets`（`[{prompt:…}]` 数组）。

## camera — 摄影机机身（9 项）

| key | 名称 | 类型 | 默认 | 追加到 prompt 的片段 |
|---|---|---|---|---|
| `sony_venice` | Sony Venice | Digital |  | `, clean digital look, 8k uhd` |
| `arri_alexa_35` | Arri Alexa 35 | Digital |  | `, cinematic color grading, soft highlights` |
| `arri_alexa_65` | Arri Alexa 65 | Digital |  | `, Shot on ARRI Alexa 65, large format cinematography, hyper-realistic, cinematic lighting, 8k resolution, movie still` |
| `red_v_raptor` | Red V-Raptor | Digital |  | `, high contrast, sharp focus` |
| `panavision_dxl2` | Panavision DXL2 | Digital | ✅ | `, Hollywood movie style` |
| `arricam_lt` | Arricam LT | Film |  | `, Shot on Arricam LT, Kodak Vision3 500T, pin sharp focus, organic medium film grain, soft highlight roll-off, rich color density, faint red halo at the edge of the light source, highly detailed texture.` |
| `arriflex_435` | ArriFlex 435 | Film |  | `, Shot on Arriflex 435, Kodak Vision3 250D 5207 style, pin sharp focus, medium film grain, soft highlight roll-off, high dynamic range, rich color density` |
| `imax_keighley` | IMAX Keighley | Film |  | `, shot on IMAX Keighley, Kodak Vision3 500T style, extremely sharp focus, high dynamic range, Extremely shallow depth of field, 18k resolution, hyper-realistic skin texture, organic film grain, 3D separation, color graded, volumetric lighting, epic scale` |
| `imax_film_camera` | IMAX Film Camera | Film |  | `, high resolution, fine film grain` |

## lens — 镜头（10 项）

| key | 名称 | 类型 | 默认 | 追加到 prompt 的片段 |
|---|---|---|---|---|
| `zeiss_ultra_prime` | Zeiss Ultra Prime |  |  | `, using Zeiss Ultra Prime, clinically sharp, high contrast` |
| `cooke_sf_18x` | Cooke SF 1.8x |  |  | `, using Cooke Anamorphic SF, Identify the light source, golden lens flare, oval bokeh, Full Frame Anamorphic, warm cinematic look` |
| `canon_k35` | Canon K-35 |  |  | `, using Canon K-35 lens, soft contrast, golden lens flare` |
| `cooke_s4` | Cooke S4 |  |  | `, using Cooke S4 lens, The Cooke Look, creamy bokeh` |
| `cooke_speed_panchro` | Cooke Panchro |  |  | `, using Cooke Speed Panchro Series III, buttery background blur, The Cooke Look, warm organic tones, soft sharpness, atmospheric depth` |
| `arri_signature_prime` | Arri Signature Prime |  | ✅ | `, using Arri Signature Prime, clean image, perfect optics` |
| `helios` | Helios |  |  | `, using Helios 44-2 lens, swirly bokeh, twisted background` |
| `panavision_c_series` | Panavision C-series |  |  | `, anamorphic cinematic look, distinct blue horizontal lens flare, oval bokeh` |
| `panavision_primo` | Panavision Primo |  |  | `, using Panavision Primo Anamorphic, oval bokeh, Anamorphic format, horizontal blue lens flare, 2x squeeze, anamorphic look` |
| `hawk_class_x` | Hawk Class X |  |  | `, using Hawk Class X Anamorphic, identify the light source, subtle creamy vertical oval bokeh, organic sharpness, vintage modern aesthetic, soft horizontal flare` |

## focal — 焦段（7 项）

| key | 名称 | 类型 | 默认 | 追加到 prompt 的片段 |
|---|---|---|---|---|
| `8mm` | 8mm |  |  | `, 8mm prime lens, exaggerated perspective, Rectilinear, immense sense of scale, stretching at edges` |
| `14mm` | 14mm |  |  | `, 14mm prime lens, rectilinear distortion, moderate linear perspective, subtle edge stretch, spatial depth, soft vignetting` |
| `24mm` | 24mm |  |  | `, 24mm prime lens, minimal rectilinear distortion, natural linear perspective, sharp corner details, cinematic natural framing, mild vignetting` |
| `35mm` | 35mm |  | ✅ | `, 35mm prime lens, near-zero rectilinear distortion, human-eye natural perspective, sharp full-frame details, subtle vignetting, candid cinematic framing` |
| `50mm` | 50mm |  |  | `, 50mm prime lens, zero distortion, eye-like perspective, close-up, subject focus, ultra shallow DOF, sharp center, faint vignetting` |
| `75mm` | 75mm |  |  | `, 75mm prime lens, zero distortion, strong compression, extreme tight close, subject full dominance, extreme shallow DOF, sharp center, faint vignetting` |
| `125mm` | 125mm |  |  | `, 125mm macro lens, 1:1 magnification, extreme compression, microscopic view, razor-sharp details, total background isolation, creamy bokeh, texture focused` |

## aperture — 光圈（3 项）

| key | 名称 | 类型 | 默认 | 追加到 prompt 的片段 |
|---|---|---|---|---|
| `f/1.4` | ƒ/1.4 |  |  | `, shallow depth of field, creamy bokeh, out-of-focus background` |
| `f/4` | ƒ/4 |  | ✅ | `, f/4 aperture, infinite depth of field, razor-sharp details, hyperfocal distance` |
| `f/11` | ƒ/11 |  |  | `, f/11 aperture, deep depth of field, crystal clear background, everything in focus` |
