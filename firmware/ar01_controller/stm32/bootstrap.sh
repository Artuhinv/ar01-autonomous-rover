#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo 'This bootstrap supports Linux x86_64; use bootstrap.ps1 on Windows.' >&2
  exit 2
fi
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cache_root="${AR01_P2_CACHE_ROOT:-${XDG_CACHE_HOME:-$HOME/.cache}/ar01-p2}"
mkdir -p "$cache_root"
toolchain_bin="${AR01_TOOLCHAIN_BIN:-$cache_root/arm-gnu-toolchain-12.3.rel1-x86_64-arm-none-eabi/bin}"
cube_g4="${AR01_CUBEG4_PATH:-$cache_root/STM32CubeG4-v1.6.3}"
managed_cube=1
if [[ -n "${AR01_CUBEG4_PATH:-}" ]]; then managed_cube=0; fi
arm_archive='arm-gnu-toolchain-12.3.rel1-x86_64-arm-none-eabi.tar.xz'
arm_url="https://developer.arm.com/-/media/Files/downloads/gnu/12.3.rel1/binrel/$arm_archive"
arm_sha256='12a2815644318ebcceaf84beabb665d0924b6e79e21048452c5331a56332b309'
cube_commit='d11b194a9f05d1b143d154771f3dbc282c8052a5'

if [[ ! -f "$toolchain_bin/arm-none-eabi-gcc" ]]; then
  archive_path="$cache_root/$arm_archive"
  if [[ ! -f "$archive_path" ]]; then
    echo 'Downloading official Arm GNU 12.3.Rel1 toolchain...'
    curl --fail --location --retry 2 --silent --show-error \
      --output "$archive_path" "$arm_url"
  fi
  actual_hash="$(sha256sum "$archive_path" | cut -d ' ' -f 1)"
  if [[ "$actual_hash" != "$arm_sha256" ]]; then
    echo "Arm archive SHA256 mismatch: $archive_path" >&2
    exit 1
  fi
  install_dir="$(dirname "$toolchain_bin")"
  if [[ -e "$install_dir" ]]; then
    echo "Incomplete toolchain directory: $install_dir; inspect before retrying" >&2
    exit 1
  fi
  tar -xJf "$archive_path" -C "$cache_root"
fi

if (( managed_cube )) && [[ ! -d "$cube_g4/.git" ]]; then
  if [[ -e "$cube_g4" ]]; then
    echo "Existing non-Git CubeG4 path: $cube_g4" >&2
    exit 1
  fi
  git clone --filter=blob:none --sparse --depth 1 --branch v1.6.3 \
    https://github.com/STMicroelectronics/STM32CubeG4.git "$cube_g4"
fi
if (( managed_cube )); then
  git -C "$cube_g4" sparse-checkout set Drivers
  git -C "$cube_g4" submodule update --init --depth 1 \
    Drivers/STM32G4xx_HAL_Driver Drivers/CMSIS/Device/ST/STM32G4xx
fi
if [[ "$(git -C "$cube_g4" rev-parse HEAD)" != "$cube_commit" ]]; then
  echo "STM32CubeG4 commit differs from pinned $cube_commit" >&2
  exit 1
fi

python3 "$script_dir/verify_ioc.py"
bash "$script_dir/build.sh" "$toolchain_bin" "$cube_g4"
