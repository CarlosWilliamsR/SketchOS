AS       := nasm
CC       := i686-elf-gcc
LD       := i686-elf-ld
OBJCOPY  := i686-elf-objcopy

BUILD_DIR := build
BOOT_SRC  := $(wildcard src/boot/*.asm)
KERNEL_SRC := $(wildcard src/kernel/*.c)
BOOT_OBJ  := $(patsubst src/boot/%.asm,$(BUILD_DIR)/boot/%.o,$(BOOT_SRC))
KERNEL_OBJ := $(patsubst src/kernel/%.c,$(BUILD_DIR)/kernel/%.o,$(KERNEL_SRC))

CFLAGS := -ffreestanding -m32 -O2 -Wall -Wextra -Iinclude
LDFLAGS := -m elf_i386 -T linker.ld

.PHONY: all clean

all: $(BUILD_DIR)/kernel.bin

$(BUILD_DIR)/kernel.bin: $(BOOT_OBJ) $(KERNEL_OBJ) linker.ld
	@mkdir -p $(BUILD_DIR)
	$(LD) $(LDFLAGS) -o $(BUILD_DIR)/kernel.elf $(BOOT_OBJ) $(KERNEL_OBJ)
	$(OBJCOPY) -O binary $(BUILD_DIR)/kernel.elf $@

$(BUILD_DIR)/boot/%.o: src/boot/%.asm
	@mkdir -p $(@D)
	$(AS) -f elf32 $< -o $@

$(BUILD_DIR)/kernel/%.o: src/kernel/%.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf $(BUILD_DIR)