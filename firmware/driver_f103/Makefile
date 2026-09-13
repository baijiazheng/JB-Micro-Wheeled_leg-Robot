# Makefile — 驱动板 F103 固件 (HAL + 自写 FOC + LQR 平衡 + CAN)
#
# 用法:
#   make        编译出 driver_f103.elf / .bin
#   make flash  用 ST-Link 烧录
#   make clean  清理
#
# 依赖: STM32CubeF1 HAL (本机 ~/STM32Cube/Repository/STM32CubeF1-1.8.6)

TARGET   = driver_f103
MCU      = cortex-m3

# ---- STM32CubeF1 位置 ----
CUBE = $(HOME)/STM32Cube/Repository/STM32CubeF1-1.8.6/Drivers

# ---- 工具链 ----
CC      = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE    = arm-none-eabi-size

# ---- 编译标志 ----
CFLAGS = -mcpu=$(MCU) -mthumb -O0 -g3 -Wall -Wextra -ffunction-sections -fdata-sections
CFLAGS += -DSTM32F103xB -DUSE_HAL_DRIVER
CFLAGS += -I Core/Inc -I app -I hal -I foc -I balance -I ../common/pid -I ../common/can_protocol
CFLAGS += -I $(CUBE)/STM32F1xx_HAL_Driver/Inc
CFLAGS += -I $(CUBE)/CMSIS/Core/Include
CFLAGS += -I $(CUBE)/CMSIS/Device/ST/STM32F1xx/Include

LDFLAGS = -mcpu=$(MCU) -mthumb -T STM32F103C8Tx_FLASH.ld -Wl,--gc-sections -Wl,-Map=$(TARGET).map
LIBS    = -lm

# ---- HAL 源文件 (排除 *_template.c, 那是模板不该编译) ----
HAL_SRC = $(filter-out %_template.c, $(wildcard $(CUBE)/STM32F1xx_HAL_Driver/Src/*.c))

# ---- 我的源文件 ----
APP_SRC = Core/Src/main.c Core/Src/stm32f1xx_it.c Core/Src/system_stm32f1xx.c \
          app/control_loop.c \
          hal/pwm.c hal/as5600.c hal/mpu6050.c hal/can_bus.c \
          foc/foc_math.c foc/foc_control.c \
          balance/balance.c \
          ../common/pid/pid.c ../common/can_protocol/can_protocol.c

ASM_SRC = Core/Startup/startup_stm32f103xb.s

OBJS = $(HAL_SRC:.c=.o) $(APP_SRC:.c=.o) $(ASM_SRC:.s=.o)

all: $(TARGET).elf $(TARGET).bin

$(TARGET).elf: $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $(OBJS) $(LIBS)
	$(SIZE) $@

$(TARGET).bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

%.o: %.s
	$(CC) $(CFLAGS) -c -o $@ $<

flash: $(TARGET).bin
	st-flash write $< 0x08000000

clean:
	rm -f $(OBJS) $(TARGET).elf $(TARGET).bin $(TARGET).map

.PHONY: all flash clean
