"""Static P2.0 pin/clock guard for the checked-in CubeMX 6.18.1 project.

This cannot replace CubeMX's pin-conflict validation or measurements on a board.
"""

from pathlib import Path


def main() -> None:
    ioc = Path(__file__).with_name("ar01_nucleo_g431rb.ioc")
    settings = dict(
        line.split("=", 1)
        for line in ioc.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    pins = {
        "PA0": "S_TIM2_CH1", "PA1": "S_TIM2_CH2",
        "PB6": "S_TIM4_CH1", "PB7": "S_TIM4_CH2",
        "PA8": "S_TIM1_CH1", "PA9": "S_TIM1_CH2",
        "PA2": "LPUART1_TX", "PA3": "LPUART1_RX",
        "PA4": "ADC2_IN17", "PB0": "ADC1_IN15", "PC0": "ADC1_IN6",
        "PC2": "GPIO_Input", "PC3": "GPIO_Input", "PB5": "GPIO_Input",
        "PC6": "GPIO_Output", "PC7": "GPIO_Output",
        "PC8": "GPIO_Output", "PC9": "GPIO_Output",
        "PA13": "SYS_JTMS-SWDIO", "PA14": "SYS_JTCK-SWCLK",
    }
    for pin, signal in pins.items():
        assert settings[f"{pin}.Signal"] == signal, pin
    assigned = [settings[f"Mcu.Pin{i}"] for i in range(int(settings["Mcu.PinsNb"]))]
    assert len(assigned) == len(set(assigned)), "duplicate pin assignment"
    for pin in pins:
        assert pin in assigned, f"{pin} absent from MCU pin list"
    for timer in ("TIM2", "TIM4"):
        assert settings[f"{timer}.EncoderMode"] == "TIM_ENCODERMODE_TI12"
    assert settings["LPUART1.BaudRate"] == "115200"
    assert settings["ProjectManager.TargetToolchain"] == "Makefile"
    pwm_hz = int(settings["RCC.APB2TimFreq_Value"]) // (
        (int(settings.get("TIM1.Prescaler", "0")) + 1)
        * (int(settings["TIM1.Period"]) + 1)
    )
    control_hz = int(settings["RCC.APB1TimFreq_Value"]) // (
        (int(settings["TIM6.Prescaler"]) + 1)
        * (int(settings["TIM6.Period"]) + 1)
    )
    assert pwm_hz == 20_000, pwm_hz
    assert control_hz == 100, control_hz
    assert settings["IWDG.Prescaler"] == "IWDG_PRESCALER_64"
    assert settings["IWDG.Reload"] == "99"
    print(f"IOC static guard: PASS ({len(pins)} pins, {pwm_hz} Hz PWM, {control_hz} Hz tick)")
    print("Note: ADC1 VIN rank, analog scaling, board solder bridges and physical LOW remain UNVERIFIED")


if __name__ == "__main__":
    main()
