/**
 * @file    as5600.c
 * @brief   AS5600 磁编码器 I2C 驱动实现 (STM32F103 HAL)
 */

#include "as5600.h"
#include "stm32f1xx_hal.h"

#define TWO_PI_F 6.28318530718f

void as5600_init(As5600 *enc, void *hi2c)
{
    enc->hi2c = hi2c;
}

int as5600_read_raw(const As5600 *enc)
{
    I2C_HandleTypeDef *hi2c = (I2C_HandleTypeDef *)enc->hi2c;
    uint8_t data[2] = {0, 0};
    HAL_StatusTypeDef st;

    /* 读 RAW ANGLE 寄存器 (0x0C), 2 字节大端 */
    st = HAL_I2C_Mem_Read(hi2c,
                          (uint16_t)(AS5600_I2C_ADDR << 1),
                          AS5600_REG_RAW_ANGLE,
                          I2C_MEMADD_SIZE_8BIT,
                          data, 2, 100);
    if (st != HAL_OK) {
        return -1; /* 读失败 */
    }
    return (int)((data[0] << 8) | data[1]); /* 12 位, 高字节在前 */
}

float as5600_read_radians(const As5600 *enc)
{
    int raw = as5600_read_raw(enc);
    if (raw < 0) {
        return 0.0f;
    }
    return ((float)raw / 4096.0f) * TWO_PI_F;
}
