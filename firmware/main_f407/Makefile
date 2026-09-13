# Makefile — 主控板 F407 固件 (HAL + STS3032 舵机 + CAN 主机)
#
# 用法: make / make flash / make clean
# 依赖: STM32CubeF4 HAL (~/STM32Cube/Repository/STM32Cube_FW_F4_V1.28.3)

TARGET = main_f407
MCU    = cortex-m4
FPU    = fpv4-sp-d16

CUBE = $(HOME)/STM32Cube/Repository/STM32Cube_FW_F4_V1.28.3/Drivers

CC      = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE    = arm-none-eabi-size

CFLAGS = -mcpu=$(MCU) -mthumb -mfpu=$(FPU) -mfloat-abi=hard -O0 -g3 -Wall -Wextra
CFLAGS += -ffunction-sections -fdata-sections
CFLAGS += -DSTM32F407xx -DUSE_HAL_DRIVER
CFLAGS += -I Core/Inc -I app -I hal -I ../common/can_protocol
CFLAGS += -I $(CUBE)/STM32F4xx_HAL_Driver/Inc
CFLAGS += -I $(CUBE)/CMSIS/Include
CFLAGS += -I $(CUBE)/CMSIS/Device/ST/STM32F4xx/Include

LDFLAGS = -mcpu=$(MCU) -mthumb -mfpu=$(FPU) -mfloat-abi=hard \
          -T STM32F407VGTx_FLASH.ld -Wl,--gc-sections -Wl,-Map=$(TARGET).map
LIBS = -lm

HAL_SRC = $(filter-out %_template.c, $(wildcard $(CUBE)/STM32F4xx_HAL_Driver/Src/*.c))

APP_SRC = Core/Src/main.c Core/Src/stm32f4xx_it.c Core/Src/system_stm32f4xx.c \
          app/main_control.c \
          hal/sts3032.c \
          ../common/can_protocol/can_protocol.c

ASM_SRC = Core/Startup/startup_stm32f407xx.s

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
