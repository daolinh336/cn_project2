import subprocess
import glob
import os

# --- Cấu hình ---
# Đường dẫn đến script network.py 
NETWORK_SCRIPT_PATH = "network.py"
# Loại router để kiểm tra
ROUTER_TYPE = "DV"
# Thông báo thành công cần tìm trong output
SUCCESS_MESSAGE = "SUCCESS: All Routes correct!"
# Thời gian tối đa cho mỗi bài test (giây)
TIMEOUT_SECONDS = 100

def run_test_on_json(json_file):
    """
    Chạy kiểm tra trên một tệp JSON cụ thể và trả về (True, output) nếu thành công,
    ngược lại trả về (False, output).
    """
    print(f"Đang kiểm tra tệp: {json_file}...")
    command = ["python", NETWORK_SCRIPT_PATH, json_file, ROUTER_TYPE]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False  
        )

        full_output = result.stdout + result.stderr 

        if SUCCESS_MESSAGE in result.stdout: # Thông báo thành công ở stdout
            print(f"  THÀNH CÔNG: {json_file} đã vượt qua.")
            return True, full_output
        else:
            print(f"  THẤT BẠI: {json_file} không vượt qua.")
            return False, full_output

    except FileNotFoundError:
        error_msg = f"LỖI: Không tìm thấy tập lệnh '{NETWORK_SCRIPT_PATH}' hoặc 'python'. "
        print(error_msg)
        return "SCRIPT_NOT_FOUND", error_msg
    except subprocess.TimeoutExpired:
        error_msg = f"  THẤT BẠI (Hết giờ): {json_file} mất quá {TIMEOUT_SECONDS} giây để chạy."
        print(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"  LỖI khi chạy {json_file}: {e}"
        print(error_msg)
        return False, error_msg

def main():
    """
    Hàm chính để tìm các tệp JSON và chạy kiểm tra.
    """
    json_files = sorted(glob.glob("*.json")) 
    if not json_files:
        print("Không tìm thấy tệp .json nào trong thư mục hiện tại.")
        return
    print(f"Tìm thấy {len(json_files)} tệp .json. Bắt đầu kiểm tra với {ROUTER_TYPE}router...")
    print("-" * 30)

    failed_tests_details = {} 
    passed_count = 0

    for json_file in json_files:
        status, output = run_test_on_json(json_file)
        if status == "SCRIPT_NOT_FOUND":
            return
        if status: 
            passed_count += 1
        else:
            failed_tests_details[json_file] = output
        print("-" * 30)

    print("\n--- TÓM TẮT KIỂM TRA ---")
    total_files = len(json_files)
    print(f"Tổng số tệp .json đã kiểm tra: {total_files}")
    print(f"Số bài kiểm tra thành công: {passed_count}")
    print(f"Số bài kiểm tra thất bại: {len(failed_tests_details)}")

    if failed_tests_details:
        print("\nCÁC BÀI KIỂM TRA SAU ĐÃ THẤT BẠI:")
        for file_name, out_text in failed_tests_details.items():
            print(f"\n--- Lỗi chi tiết cho: {file_name} ---")
            max_output_lines = 20
            output_lines = out_text.splitlines()
            for i, line in enumerate(output_lines):
                if i < max_output_lines:
                    print(line)
                elif i == max_output_lines:
                    print("... (output đã được cắt bớt) ...")
                    break
            print("-" * (len(file_name) + 25)) 
    else:
        if total_files > 0: # Chỉ in nếu có file để test
             print("\nTất cả các bài kiểm tra đã vượt qua thành công!")
        else:
             print("\nKhông có bài kiểm tra nào được thực hiện.")
    print("--- KẾT THÚC ---")

if __name__ == "__main__":
    main()
