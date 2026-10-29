# REP-159 Feature & Branch Registry

Este documento registra la secuencia cronológica de **Features**, las **Ramas Git** asociadas en cada submódulo, su rama base, estado de validación y la estrategia de integración/rebase para Upstream.

---

## 1. Estrategia de Ramas (Branching Model)

Para mantener la máxima compatibilidad, trazabilidad y facilidad al enviar Pull Requests:

1. **Ramas de Feature Limpias (`feat/<name>`)**:
   - Se cortan directamente desde **`master`** de cada repositorio (sin arrastrar commits experimentales o fixes temporales).
   - Son las candidatas directas a Pull Requests limpios hacia los repositorios oficiales de Open Robotics.
2. **Ramas de Integración / Test (`test/rep159-<name>`)**:
   - Se basan en la rama de desarrollo `rep159` donde conviven las características conjuntas del test harness.
   - Se utilizan para generar y desplegar jobs en el cluster local de Jenkins (`192.168.30.206:8080`).
3. **Sin sobreescritura ("No pisar lo que se usa")**:
   - Ninguna rama en producción o en uso activo (`master`, `rep159`) se pisa forzadamente. Todas las iteraciones avanzan como ramas nuevas e independientes.

---

## 2. Matriz de Seguimiento de Features

```
[FEAT-1: binary_rule] ──► [FEAT-2: install_rule] ──► [FEAT-3: buildfarm naming] ──► [FEAT-4: reps doc] ──► [FEAT-5: release pipeline & APT repo] ──► [FEAT-6: multi-tier topologies] ──► [FEAT-7: composable suite & ros_workspace]
  (rosdistro/rosdep)       (distro/buildfarm)          (buildfarm common.py)        (submodules/reps)        (reprepro/docker & release jobs)         (extendable family A->B->C)              (bloom fork / ros_workspace deb / C*)
```

| ID | Feature / Componente | Repositorio | Rama de Desarrollo | Rama Base | Estado Local | Estado CI Jenkins |
|---|---|---|---|---|:---:|:---:|
| **FEAT-0** | Baseline REP-159 MVP (Walk, ABI guardrails, formato 3) | `rosdistro`<br>`rosdep`<br>`ros_buildfarm`<br>`ros_buildfarm_config` | `rep159`<br>`rep159`<br>`rep159`<br>`rep159` | `master`<br>`master`<br>`master`<br>`master` | ✅ 100% (Suites 1-5) | ✅ **SUCCESS** (5/5 jobs) |
| **FEAT-1** | Motor de Renombrado Regex (`binary_rule`) | `rosdistro`<br>`rosdep` | `feature/rep159-binary-naming-regex`<br>`rep159` | `rep159`<br>`master` | ✅ 100% (Suite 6) | ⏳ Pendiente build con debs |
| **FEAT-2** | Prefijos de Instalación y Underlays Dinámicos (`install_rule`) | `rosdistro`<br>`ros_buildfarm`<br>`ros_buildfarm_config`<br>`rep159-rosdistro` | `feature/rep159-install-rule`<br>**`feat/install-prefixes`**<br>`feat/install-rule`<br>`feat/install-rule` | `feature/rep159-binary-naming-regex`<br>**`master`**<br>`rep159`<br>`feat/binary-naming-rule` | ✅ 100% (Suite 7) | ✅ **SUCCESS** (`Bci` #7) |
| **FEAT-3** | Delegación de Nombres Binarios en `ros_buildfarm` (`binary_rule`) | `ros_buildfarm`<br>`ros_buildfarm_config`<br>`rep159-rosdistro`<br>`upstream_a-release` | **`feat/binary-naming-rule`**<br>`feat/binary-naming-rule`<br>`feat/binary-naming-rule`<br>`debian/vendor-upstream/resolute/upstream_a` | **`master`**<br>`rep159`<br>`main`<br>`master` | ✅ 100% (6 unit tests) | ✅ **SUCCESS** (`Usrc` #11, `Ubin` #7) |
| **FEAT-5** | Tubería de Release, Import y Sync (`reprepro` + SSH + Nginx) | `ros_buildfarm`<br>`ros_buildfarm_config`<br>`rep159-testing` | `test/rep159-release-pipeline`<br>`rep159`<br>`main` | `test/rep159-install-prefixes`<br>`master`<br>`main` | ✅ 100% (Repo activo en :8088 con GPG) | ✅ **SUCCESS** (`Usrc_uR` #10, `Ubin` #4, `Urel_sync` #4, `Bci` #4) |
| **FEAT-6** | Encadenamiento Multi-Tier y Topologías Mixtas ($A \to B \to C$) | `rosdistro`<br>`ros_buildfarm`<br>`ros_buildfarm_config`<br>`rep159-rosdistro`<br>`downstream_bin_a-release` | `feature/rep159-install-rule`<br>`feat/binary-naming-rule`<br>`feat/stage3-binary-chained`<br>`feat/stage3-binary-chained`<br>`release/extendablebin/downstream_bin_a` | `master`<br>`master`<br>`feat/stage3-chained-extensions`<br>`feat/stage3-chained-extensions`<br>`upstream` | ✅ Opción A 100% (Local #3)<br>🔄 Opción B con fix `dd2825e` | ✅ Opción A 100% (Remoto #2)<br>⏳ Opción B en planificación |
| **FEAT-7** | Stage 4: Suite `composable`, `ros_workspace` Sourcing & Bloom Fork | `bloom`<br>`ros_workspace`<br>`ros_workspace-release`<br>`upstream_{a,b,c}-release`<br>`rep159-rosdistro`<br>`ros_buildfarm_config` | `feat/rep159-rules-support`<br>`feat/composable-underlay-chaining`<br>`debian/vendor-composable/resolute/ros_workspace`<br>`debian/vendor-composable/resolute/upstream_{a,b,c}`<br>`feat/composable-distro`<br>`feat/composable-distro` | `master`<br>`main`<br>`debian/vendor-composable`<br>`debian/vendor-composable`<br>`master`<br>`master` | ✅ 100% (Local 5-step test) | ✅ **SUCCESS** (`Csrc` #5, `Cbin` #3, `Crel_sync` #5, `Cci` #3) |

---

## 3. Detalle por Feature

### FEAT-1: Motor de Renombrado de Binarios (`binary_rule`)
- **Problema**: `rosdistro` y `rosdep` asumían rígidamente la convención `ros-{distro}-{package}`.
- **Solución**:
  - Implementación de `binary_rule` en `DistributionFile` y `ReleaseRepositorySpecification` con soporte de regex (`search`, `replace`), variables `{distro}` y `{package}`, y grupos de captura (`\1`).
  - `rosdep` delega el cálculo llamando a `rosdistro.get_binary_package_name()`.
- **Ramas publicadas en GitHub**:
  - `rep159-testing/rosdistro`: `feature/rep159-binary-naming-regex`
- **Validador local**: `tools/validate_binary_naming.py` (Suite 6).

---

### FEAT-2: Prefijos de Instalación y Underlays (`install_rule`)
- **Problema**: El fix previo de José Luis Rivero (`commit 9807b32`) hardcodeaba `/opt/ros/%s` para distribuciones padre con `binary_import`. Si la distro padre vive en `/opt/vendor` o `/usr` (Gazebo), fallaba.
- **Solución**:
  - `rosdistro`: Agregado `install_rule` a nivel distribución y repositorio, soportando plantillas (`/opt/vendor/{distro}`) y regex search/replace.
  - `ros_buildfarm`: Implementado `get_binary_import_underlays()`, `get_distribution_install_prefix()` y variable `ROS_BUILDFARM_PARENT_RESULT_SPACES`.
- **Ramas publicadas en GitHub**:
  - `rep159-testing/rosdistro`: `feature/rep159-install-rule`
  - `rep159-testing/ros_buildfarm`: `feat/install-prefixes` *(cortada limpia desde `master`)*
  - `rep159-testing/ros_buildfarm`: `test/rep159-install-prefixes` *(rama de integración sobre `rep159` para CI)*
- **Validador local**: `tools/validate_install_prefixes.py` (Suite 7).
- **Verificación en Jenkins**: `Bci__nightly-release_ubuntu_resolute_amd64` Build #2 finalizado en **SUCCESS**.

---

### FEAT-3: Delegación de Nombres Binarios en `ros_buildfarm`
- **Problema**: En `ros_buildfarm/common.py`, `get_os_package_name()` y `get_os_package_name_prefix()` forzaban rígidamente `'ros-%s-%s' % (rosdistro_name, ros_package_name.replace('_', '-'))`, ignorando si una distribución o paquete definía `binary_rule`. Asimismo, los scripts y templates del pipeline de release (`sourcedeb_job.py`, `binarydeb_job.py`, `create_binarydeb_task_generator.py`, `append_build_timestamp.py`, `build_binarydeb.py`, `trigger_job.py`, `sourcerpm_job.py`, `binaryrpm_job.py`) invocaban `get_os_package_name` sin pasar `dist_file`.
- **Solución implementada**:
  - `common.py`: Actualizado `get_os_package_name(rosdistro_name, ros_package_name, dist_file=None)` para consultar `dist_file.get_binary_package_name(ros_package_name)`.
  - `common.py`: Actualizado `get_os_package_name_prefix(rosdistro_name, dist_file=None)` para resolver el prefijo dinámico si `dist_file.binary_rule` define un prefijo regex (`^`).
  - `release_job.py`, `sourcedeb_job.py`, `binarydeb_job.py`, `create_binarydeb_task_generator.py`: Pasan `dist_file=dist_file` y propagan `debian_package_name` para la descarga, renombrado, extracción e invocación de herramientas debian/rpm.
  - Mantiene 100% de compatibilidad con llamadas existentes que no pasan `dist_file`.
- **Ramas publicadas en GitHub**:
  - `rep159-testing/ros_buildfarm`: **`feat/binary-naming-rule`** *(cortada limpia desde `master`)*
  - `rep159-testing/ros_buildfarm`: `test/rep159-release-pipeline` *(rama de integración con pipeline local)*
  - `rep159-testing/rep159-rosdistro`: `feat/binary-naming-rule` *(con `binary_rule: {search: '^', replace: 'vendor-{DISTRO}-'}`)*
  - `rep159-testing/upstream_a-release`: `debian/vendor-upstream/resolute/upstream_a` y tag `debian/vendor-upstream-upstream-a_0.1.0-1_resolute`.
- **Validador local**: `test/test_binary_naming_rule.py` (6 unit tests PASSED 100%).
- **Verificación en Jenkins**:
  - `Usrc_uR__upstream_a__ubuntu_resolute__source` #11 **SUCCESS**: empaquetó e importó en reprepro `vendor-upstream-upstream-a 0.1.0-1resolute`.
  - `Ubin_uR64__upstream_a__ubuntu_resolute_amd64__binary` #6 (en ejecución).

---

### FEAT-4: Formalización en texto de REP-159 (Rationale & Reglas Unificadas)
- **Problema**: REP-159 requería documentar la justificación técnica de la elección de mecanismos de transformación (Regex vs. EmPy vs. Jinja2) y formalizar la especificación de directorios de instalación (`install_prefix_rules`).
- **Solución implementada**:
  - En `_posts/rep-0159:2026.md`, se agregó la sección `Installation Directory Resolution` definiendo `install_prefix` e `install_prefix_rules`.
  - Se completó la sección `Rationale` en inglés argumentando por qué se eligió Regex (cero dependencias externas, determinista, seguro frente a ejecución de código arbitrario y fácilmente invertible para mapeo reverso) y cómo se unificó la lógica para el path de instalación.
  - Se documentó la validación práctica en el banco de pruebas `rep159-testing`.
- **Rama en submódulo `reps`**:
  - `submodules/reps`: `feature/rep-2015-naming-and-install-rules` (basada en `feature/rep-2015-binary-name-templating`).

---

### FEAT-5: Tubería de Release y Repositorio APT Local (`reprepro` + Nginx)
- **Problema**: Validar el flujo completo de release (source $\rightarrow$ binarydeb $\rightarrow$ repositorio APT $\rightarrow$ snapshot) localmente sin requerir permisos ni publicar en los servidores oficiales de OSRF (`repo.ros2.org` / `repo.test.ros2.org`).
- **Solución implementada**:
  - Se desplegó un servidor APT local en Docker host (`192.168.30.202:8088`) con `reprepro` y `nginx:alpine` para la suite `resolute` en canales `building`, `shadow-fixed` y `main`.
  - Se configuró firma GPG determinista (`Local ROS Buildfarm <buildfarm@local>`) con clave servida vía HTTP (`/ubuntu/ros-local-buildfarm.asc`).
  - Se actualizó `submodules/ros_buildfarm_config/index-local.yaml` para incluir el repo local y su clave pública GPG.
  - Se implementó la rama de integración `test/rep159-release-pipeline` en `ros_buildfarm` inyectando los forks de `rosdistro` y `rosdep` en los templates Docker de sourcedeb y binarydeb (`sourcepkg_task.Dockerfile.em` y `binarypkg_task.Dockerfile.em`).
  - Se implementó el script `scripts/switch_target_farm.sh` para conmutar fácilmente entre ejecución local y remota (`build.test.ros2.org`).
- **Ramas y Componentes**:
  - `submodules/ros_buildfarm`: `test/rep159-release-pipeline` *(integración sobre `test/rep159-install-prefixes` + `feat/binary-naming-rule`)*
  - `submodules/ros_buildfarm_config`: Rama `rep159` (con `index-local.yaml` y `binext/ci-nightly-release-local.yaml`).
  - `rep159-testing`: Host Docker `.202` (`/root/docker-compose.yml`, `/root/config/apt-repo`).

---

### FEAT-7: Stage 4 — Suite `composable`, Integración de `ros_workspace` y Bloom Fork
- **Problema**: Las validaciones en las etapas 1 a 3 utilizaban paquetes CMake puros (`<build_type>cmake</build_type>`), requiriendo que `ros_buildfarm` inyectara rutas (`CMAKE_PREFIX_PATH`, `LD_LIBRARY_PATH`) de forma manual. Una distribución ROS 2 real requiere que `ros_workspace` genere `/opt/ros/<distro>/setup.sh`, encadene underlays y que `bloom` respete `binary_rule` e `install_rule`.
- **Solución implementada**:
  - **Fork de Bloom (`rep159-testing/bloom`)**: En la rama `feat/rep159-rules-support`, soporte nativo para consultar `rosdistro.get_binary_package_name()` y resolver `install_rule` en `debian/rules`.
  - **Soporte de Underlay Chaining en `ros_workspace`**: En `feat/composable-underlay-chaining`, configuración para encadenar prefijos padre (`/opt/ros/upstream`) en el entorno de la distribución `composable`.
  - **Pipeline de Release y Generación de `.deb`**: Se empaquetó e instaló `vendor-composable-ros-workspace_1.0.4-1resolute` en `/opt/ros/composable` y se liberaron `vendor-composable-upstream-{a,b,c}`.
  - **Validación en CI con Sourcing Nativo**: `Cci__nightly-release_ubuntu_resolute_amd64` instaló `vendor-composable-ros-workspace` desde el repo `testing` en `.202` y ejecutó `colcon build` y `colcon test` sourceando `. /opt/ros/composable/setup.sh`.
- **Ramas y Componentes**:
  - `submodules/bloom`: `feat/rep159-rules-support`
  - `submodules/ros_workspace`: `feat/composable-underlay-chaining`
  - `submodules/ros_workspace-release`: `debian/vendor-composable/resolute/ros_workspace` (tag `debian/vendor-composable-ros-workspace_1.0.4-1_resolute`)
  - `submodules/upstream_{a,b,c}-release`: `debian/vendor-composable/resolute/upstream_{a,b,c}` (tags `debian/vendor-composable-upstream-{a,b,c}_0.1.0-1_resolute`)
  - `submodules/rep159-rosdistro`: `feat/composable-distro`
  - `submodules/ros_buildfarm_config`: `feat/composable-distro`
- **Verificación en Jenkins**: 5-step local pipeline 100% SUCCESS (`Csrc`, `Cbin`, `Crel_sync`, `Cci`).

---

## 4. Registro de Ejecuciones en Jenkins (Buildfarm Local)

| Job | Build # | Fecha | Rama probada | Resultado | Notas |
|:---|:---:|:---:|:---|:---:|:---|
| `Uci__nightly-release...` | #4 | 2026-10-16 | `rep159` | **SUCCESS** | Validación de baseline de upstream. |
| `Uci__source-branches...` | #1 | 2026-10-16 | `rep159` | **SUCCESS** | Validación de compilación de bootstrap. |
| `Uci__release-branches...` | #1 | 2026-10-16 | `rep159` | **SUCCESS** | Validación de dependency walk de release. |
| `Sci__nightly-release...` | #1 | 2026-10-16 | `rep159` | **SUCCESS** | `source_rebuild` cruza frontera y compila todo. |
| `Bci__nightly-release...` | #1 | 2026-10-16 | `rep159` | **SUCCESS** | `binary_import` con underlay hardcodeado. |
| `Bci__nightly-release...` | #2 | 2026-10-17 | `test/rep159-install-prefixes`<br>`feature/rep159-install-rule` | **SUCCESS** | **FEAT-2 validado**: Resolución dinámica de underlays vía variable `ROS_BUILDFARM_PARENT_RESULT_SPACES`. |
| `Usrc_uR__upstream_a__ubuntu_resolute__source` | #1 | 2026-10-17 | `feat/binary-naming-rule` | **FAILURE** | Fallo por falta de soporte de formato 3 de rosdistro en release template. |
| `Usrc_uR__upstream_a__ubuntu_resolute__source` | #10 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | Sourcedeb compilado, transferido vía SSH e importado en `building` repo. |
| `Ubin_uR64__upstream_a__ubuntu_resolute_amd64__binary` | #4 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | Binary deb y dbgsym compilados e importados en `building` repo. |
| `Usrc_uR__upstream_b__ubuntu_resolute__source` | #1 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | Sourcedeb de `upstream_b` importado en `building`. |
| `Ubin_uR64__upstream_b__ubuntu_resolute_amd64__binary` | #1 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | Binary deb de `upstream_b` compilado e importado en `building` resolviendo dep `upstream_a`. |
| `Usrc_uR__upstream_c__ubuntu_resolute__source` | #1 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | Sourcedeb de `upstream_c` importado en `building`. |
| `Ubin_uR64__upstream_c__ubuntu_resolute_amd64__binary` | #2 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | Binary deb de `upstream_c` compilado e importado en `building` resolviendo deps `upstream_b` y `upstream_a`. |
| `Urel_sync-packages-to-testing_resolute_amd64` | #4 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | Sincronización exitosa; `ros-upstream-upstream-a`, `-b` y `-c` publicados en `http://192.168.30.202:8088/ubuntu/testing`. |
| `Bci__nightly-release_ubuntu_resolute_amd64` | #4 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | **FASE 2 VALIDADA:** `downstream_bin_a` instaló `ros-upstream-upstream-c`, `-b` y `-a` desde `testing` vía `binary_import`, compiló y pasó tests 100% green. |
| `Usrc_uR__upstream_a__ubuntu_resolute__source` | #11 | 2026-10-19 | `feat/binary-naming-rule`<br>`test/rep159-release-pipeline` | **SUCCESS** | **FEAT-3 sourcedeb validado**: Construyó e importó `vendor-upstream-upstream-a 0.1.0-1resolute` en `building`. |
| `Ubin_uR64__upstream_a__ubuntu_resolute_amd64__binary` | #5 | 2026-10-19 | `test/rep159-release-pipeline` | **FAILURE** | Falló al buscar .dsc porque `binarydeb_job.py` no pasaba `dist_file` en el step interno de download. Corregido en commit `3397a12`. |
| `Ubin_uR64__upstream_a__ubuntu_resolute_amd64__binary` | #6 | 2026-10-19 | `test/rep159-release-pipeline` | **FAILURE** | Falló al resolver sourcedeb en apt porque `target_repository` en `release-build.yaml` apuntaba a `repo.test.ros2.org` en lugar del repo local. Corregido con `release-build-local.yaml`. |
| `Ubin_uR64__upstream_a__ubuntu_resolute_amd64__binary` | #7 | 2026-10-19 | `feat/binary-naming-rule`<br>`test/rep159-release-pipeline` | **SUCCESS** | **FEAT-3 binarydeb validado**: Descargó sourcedeb de repo local, compiló `vendor-upstream-upstream-a_0.1.0-1resolute..._amd64.deb` y dbgsym, e importó 100% green a `building`. |
| `Urel_sync-packages-to-testing_resolute_amd64` | #8 | 2026-10-19 | `test/rep159-release-pipeline` | **SUCCESS** | Sincronización exitosa; `vendor-upstream-upstream-a` promovido a `testing` en repo local. |
| `Bci__nightly-release_ubuntu_resolute_amd64` | #6 | 2026-10-19 | `feat/install-rule`<br>`test/rep159-release-pipeline` | **FAILURE** | Falló en `generate_install_lists.py` (`KeyError: vendor-upstream-upstream-c`): `upstream/distribution.yaml` heredaba `binary_rule` global renombrando `upstream_c`, pero en APT solo existía `ros-upstream-upstream-c`. |
| `Bci__nightly-release_ubuntu_resolute_amd64` | #7 | 2026-10-19 | `feat/install-rule`<br>`test/rep159-release-pipeline` | **SUCCESS** | **Stage 3 / FEAT-2 100% validado**: Inyección dinámica de `ROS_BUILDFARM_PARENT_RESULT_SPACES=/opt/vendor/upstream` vía `install_rule`. Colcon invocó `. /opt/vendor/upstream/setup.sh && colcon build ...`, compiló `downstream_bin_a` y pasó tests 100% green. |
| `Eci__chained-import_ubuntu_resolute_amd64` | #3 | 2026-10-20 | `feat/stage3-chained-extensions` | **SUCCESS** | **Stage 3 / Opción A Validada Localmente**: Compilación multi-paquete completa de los 5 repositorios fuente en colcon workspace. Todos los tests de Google Test (`test_downstream_bin_a` y `test_downstream_chain_a`) 100% green. |
| `Esrc_uR__downstream_bin_a__ubuntu_resolute__source` | #1 | 2026-10-20 | `feat/stage3-binary-chained` | **SUCCESS** | **Stage 3 / Opción B Sourcedeb**: Construyó y publicó `ros-extendablebin-downstream-bin-a_0.2.0-1resolute.dsc` en reprepro local `building`. Disparó binarydeb automáticamente. |
| `Ebin_uR64__downstream_bin_a__ubuntu_resolute_amd64__binary` | #1 | 2026-10-20 | `feat/stage3-binary-chained` | **SUCCESS** | **Stage 3 / Opción B Binarydeb**: Instaló `vendor-extendable-upstream-c` desde APT local, compiló `ros-extendablebin-downstream-bin-a_0.2.0-1resolute_amd64.deb` en `/opt/ros/extendablebin`, e importó exitosamente en `building`. |
| `Erel_sync-packages-to-testing_resolute_amd64` | #9 | 2026-10-20 | `feat/stage3-binary-chained` | **SUCCESS** | Sincronización exitosa; `ros-extendablebin-downstream-bin-a` promovido a `http://192.168.30.202:8088/ubuntu/testing`. |
| `Eci__chained-import_ubuntu_resolute_amd64` | #9 | 2026-10-20 | `feat/stage3-binary-chained` | **FAILURE** | **Validación binaria exitosa / Fallo de underlay en build**: APT instaló correctamente `ros-extendablebin-downstream-bin-a` y `vendor-extendable-upstream-c`. Falló en `colcon build` porque `build_and_install.py` no caía a `get_default_parent_result_spaces()` al recibir `--parent-result-space` vacío. Corregido en commit `dd2825e` de `ros_buildfarm`. |
| `Eci__chained-import_ubuntu_resolute_amd64` | #10 | 2026-10-20 | `feat/stage3-binary-chained` | **FAILURE** | Falló en `colcon build`: capas de Docker cacheadas previamente en el runner reutilizaron imagen sin `setup.sh` en underlays sin exportar variables. |
| `Eci__chained-import_ubuntu_resolute_amd64` | #11 | 2026-10-20 | `feat/stage3-binary-chained` | **FAILURE** | Falló en `find_package(downstream_bin_a 0.2)`: paquetes CMake puros en `/opt/ros/extendablebin` carecen de `setup.sh`, por lo que `workspace.py` no seteaba `CMAKE_PREFIX_PATH`. Corregido en commit `12982be`. |
| `Eci__chained-import_ubuntu_resolute_amd64` | #12 | 2026-10-20 | `feat/stage3-binary-chained` | **UNSTABLE** | **Compilación 100% exitosa**: `colcon build` encontró `downstream_bin_a` y compiló `downstream_chain_a`. Falló el test unitario en runtime (`error while loading shared libraries: libdownstream_bin_a.so: No such file or directory`) por falta de `LD_LIBRARY_PATH`. Corregido en commit `2a869d8`. |
| `Eci__chained-import_ubuntu_resolute_amd64` | #13 | 2026-10-20 | `feat/stage3-binary-chained` | **SUCCESS** | **STAGE 3 OPTION B (CHAINED BINARY IMPORT) 100% VALIDADA**: Inyección dinámica de `CMAKE_PREFIX_PATH`, `COLCON_PREFIX_PATH` y `LD_LIBRARY_PATH` multiarch. APT instaló debians `ros-extendablebin-downstream-bin-a` y transitivo `vendor-extendable-upstream-c`. `downstream_chain_a` compiló, linkeó y pasó tests de GoogleTest y CTest (1/1 green). |
| `Eci__mixed-chain_ubuntu_resolute_amd64` | #1 | 2026-10-21 | `feat/stage3-mixed` | **FAILURE** | Falló en rosdep: redefinición de `upstream_c` en `extendablemixed/distribution.yaml` bajo `binary_import` violó la regla de inmutabilidad de ABI de REP-159. Corregido permitiendo la herencia limpia de `upstream_c` sin colisión en `distribution.yaml`. |
| `Eci__mixed-chain_ubuntu_resolute_amd64` | #2 | 2026-10-21 | `feat/stage3-mixed` | **SUCCESS** | **STAGE 3 TOPOLOGY 2 (HYBRID BINARY + SOURCE) 100% VALIDADA**: `downstream_bin_a` instalado como binario desde APT (`ros-extendablebin-downstream-bin-a`). `upstream_c` clonado y compilado desde fuente en workspace, sobrescribiendo su contraparte binaria (`--ignore-src`). `downstream_chain_a` compiló y linkeó contra ambos paquetes. Tests unitarios ejecutados y pasados (2/2 green en CTest). |
| `Csrc_uR__ros_workspace__ubuntu_resolute__source` | #5 | 2026-10-28 | `debian/vendor-composable/resolute/ros_workspace` | **SUCCESS** | **Stage 4 / FEAT-7**: Construyó sourcedeb `vendor-composable-ros-workspace_1.0.4-1resolute.dsc` con prefijo `/opt/ros/composable` y exportó a `building`. |
| `Cbin_uR64__ros_workspace__ubuntu_resolute_amd64__binary` | #3 | 2026-10-28 | `debian/vendor-composable/resolute/ros_workspace` | **SUCCESS** | **Stage 4 / FEAT-7**: Compiló `vendor-composable-ros-workspace_1.0.4-1resolute_amd64.deb` generando layout de entorno, `.dsv` hooks y underlay chaining hacia `/opt/ros/upstream`. |
| `Csrc_uR__upstream_a__ubuntu_resolute__source` | #1 | 2026-10-28 | `debian/vendor-composable/resolute/upstream_a` | **SUCCESS** | Construyó sourcedeb `vendor-composable-upstream-a_0.1.0-1resolute.dsc` e importó en `building`. |
| `Cbin_uR64__upstream_a__ubuntu_resolute_amd64__binary` | #2 | 2026-10-28 | `debian/vendor-composable/resolute/upstream_a` | **SUCCESS** | Compiló e importó `vendor-composable-upstream-a_0.1.0-1resolute_amd64.deb` en `building`. |
| `Csrc_uR__upstream_b__ubuntu_resolute__source` | #1 | 2026-10-28 | `debian/vendor-composable/resolute/upstream_b` | **SUCCESS** | Construyó sourcedeb `vendor-composable-upstream-b_0.1.0-1resolute.dsc` e importó en `building`. |
| `Cbin_uR64__upstream_b__ubuntu_resolute_amd64__binary` | #3 | 2026-10-28 | `debian/vendor-composable/resolute/upstream_b` | **SUCCESS** | Compiló e importó `vendor-composable-upstream-b_0.1.0-1resolute_amd64.deb` en `building`. |
| `Csrc_uR__upstream_c__ubuntu_resolute__source` | #1 | 2026-10-28 | `debian/vendor-composable/resolute/upstream_c` | **SUCCESS** | Construyó sourcedeb `vendor-composable-upstream-c_0.1.0-1resolute.dsc` e importó en `building`. |
| `Cbin_uR64__upstream_c__ubuntu_resolute_amd64__binary` | #3 | 2026-10-28 | `debian/vendor-composable/resolute/upstream_c` | **SUCCESS** | Compiló e importó `vendor-composable-upstream-c_0.1.0-1resolute_amd64.deb` en `building`. |
| `Crel_sync-packages-to-testing_resolute_amd64` | #5 | 2026-10-28 | `feat/composable-distro` | **SUCCESS** | Promovió los 4 paquetes debian de `building` a `testing` (`vendor-composable-ros-workspace` y `vendor-composable-upstream-{a,b,c}`). |
| `Cci__nightly-release_ubuntu_resolute_amd64` | #3 | 2026-10-28 | `feat/composable-distro` | **SUCCESS** | **STAGE 4 ROOT DISTRO VALIDADA**: APT instaló `vendor-composable-ros-workspace` desde `testing`. Colcon compiló `upstream_{a,b,c}` sourceando nativamente `. /opt/ros/composable/setup.sh`. Todos los tests (CTest y GoogleTest) 100% green. |
| `Csrc_uR__downstream_bin_a__ubuntu_resolute__source` | #2 | 2026-10-28 | `debian/vendor-composablebin/resolute/downstream_bin_a` | **SUCCESS** | **Stage 4 / Composablebin Sourcedeb**: Construyó sourcedeb `vendor-composablebin-downstream-bin-a_0.2.0-1resolute.dsc` e importó en `building`. |
| `Cbin_uR64__downstream_bin_a__ubuntu_resolute_amd64__binary` | #1 | 2026-10-28 | `debian/vendor-composablebin/resolute/downstream_bin_a` | **SUCCESS** | **Stage 4 / Composablebin Binarydeb**: Instaló dependencia `vendor-composable-upstream-c` de APT, compiló con prefijo `/opt/ros/composablebin`, generó `vendor-composablebin-downstream-bin-a_0.2.0-1resolute_amd64.deb` e importó a `building`. |
| `Crel_sync-packages-to-testing_resolute_amd64` | #6 | 2026-10-28 | `feat/composable-distro` | **SUCCESS** | Sincronización exitosa; `vendor-composablebin-downstream-bin-a` promovido a `http://192.168.30.202:8088/ubuntu/testing` con filtro `Package (% vendor-composablebin-*)`. |
| `Cci__binary-import_ubuntu_resolute_amd64` | #4 | 2026-10-28 | `feat/composable-distro` | **SUCCESS** | **STAGE 4 COMPOSABLEBIN NATIVE UNDERLAY SOURCING 100% VALIDADA**: Instaló `vendor-composable-ros-workspace` desde `testing`. Invocó `. /opt/ros/composable/setup.sh` en todas las fases de colcon build y test. Compiló `downstream_bin_a` contra `vendor-composable-upstream-c`. Todos los tests (CTest/GoogleTest) 100% green. |



---

## 5. Registro de Ejecuciones en la Testfarm Remota (`build.test.ros2.org`)

| Job | Build # | Rama Probada | Resultado | Notas |
|:---|:---:|:---|:---:|:---|
| `Uci__nightly-release...` | #3 | `feat/binary-naming-rule` | **SUCCESS** | 933s. Baseline CI upstream OK. |
| `Uci__source-branches...` | #4 | `feat/binary-naming-rule` | **SUCCESS** | 953s. Compilación bootstrap upstream OK. |
| `Uci__release-branches...` | #4 | `feat/binary-naming-rule` | **SUCCESS** | 951s. Dependency walk de release upstream OK. |
| `Sci__nightly-release...` | #4 | `feat/binary-naming-rule` | **SUCCESS** | 913s. `source_rebuild` OK. |
| `Bci__nightly-release...` | #4 | `feat/binary-naming-rule` | **FAILURE** | 483s. `binary_import` falló por falta de inyección de underlay (resuelto en FEAT-2). |
| `Usrc_uR__upstream_a...` | #4 | `feat/binary-naming-rule` | **SUCCESS** | Generó y publicó `vendor-upstream-upstream-a_0.1.0-1resolute.dsc` en reprepro `building`. |
| `Ubin_uR64__upstream_a...` | #4 | `feat/binary-naming-rule` | **SUCCESS** | 4m56s. Compiló e importó `vendor-upstream-upstream-a_0.1.0-1resolute_amd64.deb` en `building`. Disparó `Urel_import-package` #16 (**SUCCESS**). |
| `Bci__nightly-release...` | #5 | `feat/install-prefixes`<br>`feat/install-rule` | **FAILURE** | 14m11s. Inyectó `/opt/vendor/upstream` pero los `.deb` remotos en `repo.test.ros2.org/ubuntu/testing` residen en `/opt/ros/upstream`. |
| `Sci__nightly-release...` | #5 | `feat/install-prefixes`<br>`feat/install-rule` | **SUCCESS** | Compilación completa de `source_rebuild` sobre `feat/install-prefixes`. |
| `Uci__nightly-release...` | #4 | `feat/install-prefixes`<br>`feat/install-rule` | **SUCCESS** | Baseline upstream OK sobre `feat/install-prefixes`. |
| `Uci__source-branches...` | #5 | `feat/install-prefixes`<br>`feat/install-rule` | **SUCCESS** | Bootstrap upstream OK sobre `feat/install-prefixes`. |
| `Uci__release-branches...` | #5 | `feat/install-prefixes`<br>`feat/install-rule` | **SUCCESS** | Release tags walk upstream OK sobre `feat/install-prefixes`. |
| `Bci__nightly-release...` | #6 | `feat/install-prefixes`<br>`feat/install-rule` | **SUCCESS** | Reconfigurado con `install_rule: /opt/ros/{distro}` coincidente con el prefijo real de los `.deb` en APT. Inyectó `/opt/ros/upstream`, resolvió `upstream_cConfig.cmake`, compiló y pasó tests 100% green. |
| `Usrc_uR__upstream_b...` | #5 | `feat/binary-naming-rule` | **SUCCESS** | Reconfigurado para clonar `feat/binary-naming-rule` de `ros_buildfarm`. Publicó `vendor-upstream-upstream-b_0.1.0-1resolute.dsc` en reprepro `building`. |
| `Ubin_uR64__upstream_b...` | #8 | `feat/binary-naming-rule` | **SUCCESS** | Corregida dependencia en `debian/control` sin pipe alternativo. Compiló e importó `vendor-upstream-upstream-b_0.1.0-1resolute_amd64.deb` en `building`. Disparó `Urel_import-package` (**SUCCESS**). |
| `Usrc_uR__upstream_c...` | #4 | `feat/binary-naming-rule` | **SUCCESS** | Generó y publicó `vendor-upstream-upstream-c_0.1.0-1resolute.dsc` en reprepro `building`. |
| `Ubin_uR64__upstream_c...` | #9 | `feat/binary-naming-rule` | **SUCCESS** | Compiló e importó `vendor-upstream-upstream-c_0.1.0-1resolute_amd64.deb` en `building` resolviendo deps de `vendor-upstream-upstream-b` y `-a`. Disparó `Urel_import-package` (**SUCCESS**). |
| `Urel_sync-packages-to-testing_resolute_amd64` | #10 | `feat/binary-naming-rule` | **SUCCESS** | Validación de criterios de sincronización 100% exitosa: verificó la presencia en `building` de `vendor-upstream-upstream-a`, `vendor-upstream-upstream-b` y `vendor-upstream-upstream-c` (`All required binary packages are available`). |
| `Eci__chained-import_ubuntu_resolute_amd64` | #2 | `feat/stage3-chained-extensions` | **SUCCESS** | CI encadenada multi-nivel (Opción A: `source_rebuild`) 100% exitosa en testfarm remota (`build.test.ros2.org`). Clonó y compiló los 5 paquetes en cascada (`upstream_a`, `upstream_b`, `upstream_c`, `downstream_bin_a`, `downstream_chain_a`), y ejecutó todos los tests unitarios con éxito. |
| `Esrc_uR__downstream_bin_a__ubuntu_resolute__source` | #1 | `debian/extendablebin/resolute/downstream_bin_a` | **SUCCESS** | **Stage 3B Sourcedeb Remoto**: Generó y publicó `ros-extendablebin-downstream-bin-a_0.2.0-1resolute.dsc` en reprepro `building` de OSRF. |
| `Ebin_uR64__downstream_bin_a__ubuntu_resolute_amd64__binary` | #1 | `debian/extendablebin/resolute/downstream_bin_a` | **SUCCESS** | **Stage 3B Binarydeb Remoto**: Descargó sourcedeb, consumió `vendor-extendable-upstream-c` de APT, compiló `ros-extendablebin-downstream-bin-a_0.2.0-1resolute_amd64.deb` e importó en `building`. |
| `Erel_sync-packages-to-testing_resolute_amd64` | #7 | `feat/stage3-binary-chained` | **SUCCESS** | **Stage 3B Sync Remoto**: Promovió `ros-extendablebin-downstream-bin-a` al repositorio público `http://repo.test.ros2.org/ubuntu/testing`. |
| `Eci__mixed-chain_ubuntu_resolute_amd64` | #1 | `feat/stage3-mixed` | **SUCCESS** | **Stage 3 Topology 2 (Hybrid Binary + Source) Remoto**: CI híbrida exitosa en runners públicos de `build.test.ros2.org`. Instaló `ros-extendablebin-downstream-bin-a` de APT, clonó y compiló `upstream_c` y `downstream_chain_a` en workspace, y ejecutó 2/2 suites de tests en verde. |




