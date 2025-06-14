#!/usr/bin/env python3
"""
Comprehensive test suite for LeRobot integration with Solo Server
Tests both the integration points and actual functionality

SETUP REQUIREMENTS:
1. Solo Server must be installed: 
   cd /path/to/solo-server && pip install -e .

2. For Docker tests, build the image first:
   cd examples/endpoints/lerobot
   docker build -t getsolo/lerobot:cpu .

3. Required Python packages for tests:
   pip install typer pyyaml

RUNNING TESTS:
- Unit tests only (no Docker): python3 test_lerobot_integration.py --unit
- All tests: python3 test_lerobot_integration.py
- With real hardware: python3 test_lerobot_integration.py --hardware
"""
import subprocess
import json
import sys
import os
import tempfile
import time
import unittest.mock as mock

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test(name, condition, error_msg=""):
    """Helper to run and report test results"""
    if condition:
        print(f"✅ {name}")
        return True
    else:
        print(f"❌ {name}")
        if error_msg:
            print(f"   Error: {error_msg}")
        return False

print("=== LeRobot Integration Test Suite ===\n")
tests_passed = 0
tests_failed = 0

# ========== SECTION 1: Core Integration Tests ==========
print("1. Core Integration Tests:")

# Test that LeRobot is properly added to ServerType enum
try:
    from solo_server.commands.serve import ServerType
    
    # Test 1: Can we create a LeRobot server type and it has correct value?
    lerobot_type = ServerType('lerobot')
    passed = test("1.1 ServerType.LEROBOT has correct value", 
                  lerobot_type.value == 'lerobot' and 
                  lerobot_type.name == 'LEROBOT',
                  f"Got value={lerobot_type.value}, name={lerobot_type.name}")
    tests_passed += passed
    tests_failed += not passed
    
    # Test 2: Is LeRobot properly integrated in enum?
    all_types = [s.value for s in ServerType]
    expected_types = ['ollama', 'vllm', 'llama.cpp', 'lerobot']
    passed = test("1.2 LeRobot in correct position in server types",
                  'lerobot' in all_types and 
                  all(t in all_types for t in expected_types),
                  f"Got types: {all_types}")
    tests_passed += passed
    tests_failed += not passed
    
    # Test 3: Enum comparison works correctly
    passed = test("1.3 ServerType enum comparison works",
                  ServerType.LEROBOT == ServerType('lerobot') and
                  ServerType.LEROBOT != ServerType.OLLAMA)
    tests_passed += passed
    tests_failed += not passed
    
except Exception as e:
    test("1.x ServerType integration", False, str(e))
    tests_failed += 3

# Test configuration loading with validation
try:
    from solo_server.config.config_loader import get_server_config
    
    config = get_server_config('lerobot')
    
    # Test 4: Config loads without error
    passed = test("1.4 LeRobot config loads successfully", 
                  config is not None and isinstance(config, dict))
    tests_passed += passed
    tests_failed += not passed
    
    # Test 5: Validate ALL required config values
    required_config = {
        'default_model': ('lerobot/act_so101', str),
        'default_port': (5070, int),
        'container_name': ('solo-lerobot', str),
        'images': (dict, type)
    }
    
    all_valid = True
    for key, (expected_val, expected_type) in required_config.items():
        if key not in config:
            test(f"1.5.{key} Config missing key", False, f"Key '{key}' not found")
            all_valid = False
        elif expected_type == type:
            # Type check for dict
            if not isinstance(config[key], expected_val):
                test(f"1.5.{key} Config type check", False, 
                     f"Expected {expected_val}, got {type(config[key])}")
                all_valid = False
        else:
            # Value and type check
            if config[key] != expected_val or not isinstance(config[key], expected_type):
                test(f"1.5.{key} Config value check", False,
                     f"Expected {expected_val} ({expected_type}), got {config[key]} ({type(config[key])})")
                all_valid = False
    
    if all_valid:
        test("1.5 All config values correct", True)
        tests_passed += 1
    else:
        tests_failed += 1
        
    # Test 6: Validate image configuration
    if 'images' in config:
        required_images = ['nvidia', 'amd', 'apple', 'cpu']
        images = config['images']
        all_images_valid = all(
            gpu in images and 
            images[gpu].startswith('getsolo/lerobot:') 
            for gpu in required_images
        )
        passed = test("1.6 All GPU images configured correctly",
                      all_images_valid,
                      f"Images: {images}")
        tests_passed += passed
        tests_failed += not passed
    else:
        test("1.6 GPU images", False, "No images in config")
        tests_failed += 1
        
except Exception as e:
    test("1.x Configuration", False, str(e))
    tests_failed += 4

# ========== SECTION 2: CLI Integration Tests ==========
print("\n2. CLI Integration Tests:")

# Test that CLI properly handles lerobot server type
with tempfile.TemporaryDirectory() as tmpdir:
    config_dir = os.path.join(tmpdir, '.solo_server')
    os.makedirs(config_dir)
    
    config = {"hardware": {"use_gpu": False}, "server": {"type": "ollama"}}
    with open(os.path.join(config_dir, 'config.json'), 'w') as f:
        json.dump(config, f)
    
    env = os.environ.copy()
    env['HOME'] = tmpdir
    
    # Test 7: CLI recognizes lerobot as valid type (not just help)
    # We'll test with a dry-run style check
    result = subprocess.run(
        ["solo", "serve", "-s", "lerobot", "--help"],
        capture_output=True,
        text=True,
        env=env
    )
    
    # Check both that it succeeds AND mentions lerobot in help
    passed = test("2.1 CLI accepts lerobot and shows in help",
                  result.returncode == 0 and 
                  ('lerobot' in result.stdout.lower() or 'lerobot' in result.stderr.lower()),
                  f"Exit: {result.returncode}, Found lerobot: {'lerobot' in (result.stdout + result.stderr).lower()}")
    tests_passed += passed
    tests_failed += not passed
    
    # Test 8: Error message for invalid type includes lerobot
    result = subprocess.run(
        ["solo", "serve", "-s", "invalid_type"],
        capture_output=True,
        text=True,
        env=env
    )
    
    error_output = result.stderr.lower()
    passed = test("2.2 Invalid server error message lists lerobot option",
                  result.returncode != 0 and 
                  'lerobot' in error_output and
                  ('valid options' in error_output or 'choose from' in error_output),
                  "Error should list valid options including lerobot")
    tests_passed += passed
    tests_failed += not passed

# ========== SECTION 3: Server Function Tests ==========
print("\n3. Server Function Tests:")

try:
    from solo_server.utils.server_utils import start_lerobot_server
    import inspect
    
    # Test 9: Function signature is correct
    sig = inspect.signature(start_lerobot_server)
    params = list(sig.parameters.keys())
    required_params = ['gpu_enabled', 'gpu_vendor', 'port', 'model_path']
    
    passed = test("3.1 start_lerobot_server has all required parameters",
                  all(p in params for p in required_params) and len(params) == len(required_params),
                  f"Got params: {params}, expected: {required_params}")
    tests_passed += passed
    tests_failed += not passed
    
    # Test 10: Function handles missing Docker image correctly
    with mock.patch('subprocess.run') as mock_run:
        # Mock: no container exists, no image exists
        mock_run.side_effect = [
            mock.Mock(stdout='', returncode=0),  # No container
            mock.Mock(stdout='', returncode=0),  # No image
        ]
        
        result = start_lerobot_server(False, None, 5070, "lerobot/act_so101")
        
        passed = test("3.2 Returns False when Docker image missing",
                      result == False,
                      f"Should return False, got {result}")
        tests_passed += passed
        tests_failed += not passed
        
        # Verify it tried to check for image
        docker_calls = [str(call) for call in mock_run.call_args_list]
        image_check = any('image' in call and 'ls' in call for call in docker_calls)
        passed = test("3.3 Checks for Docker image existence",
                      image_check,
                      "Should check if Docker image exists")
        tests_passed += passed
        tests_failed += not passed
    
    # Test 11: Function would start container with correct parameters
    with mock.patch('subprocess.run') as mock_run:
        # Mock: no container exists, image exists, container starts
        mock_run.side_effect = [
            mock.Mock(stdout='', returncode=0),  # No container
            mock.Mock(stdout='getsolo/lerobot:cpu', returncode=0),  # Image exists
            mock.Mock(stdout='container_id', returncode=0),  # Container starts
        ]
        
        result = start_lerobot_server(True, 'nvidia', 5070, "lerobot/act_so101")
        
        # Check the docker run command
        run_calls = [call for call in mock_run.call_args_list if 'run' in str(call)]
        if run_calls:
            run_cmd = str(run_calls[0])
            
            # Verify critical parameters
            has_gpu = '--gpus' in run_cmd
            has_port = '5070:5070' in run_cmd
            has_devices = '/dev/ttyUSB0' in run_cmd or '/dev/video0' in run_cmd
            has_model_env = 'MODEL_ID=lerobot/act_so101' in run_cmd
            
            passed = test("3.4 Docker run command has correct parameters",
                          has_gpu and has_port and has_devices and has_model_env,
                          f"GPU:{has_gpu}, Port:{has_port}, Devices:{has_devices}, Model:{has_model_env}")
            tests_passed += passed
            tests_failed += not passed
        else:
            test("3.4 Docker run command", False, "No run command found")
            tests_failed += 1
        
except Exception as e:
    test("3.x Server function", False, str(e))
    tests_failed += 4

# ========== SECTION 4: Endpoint Module Tests ==========
print("\n4. Endpoint Module Tests:")

endpoint_dir = "examples/endpoints/lerobot"

# Test 12-14: Files exist and have expected content
files_to_validate = [
    ('server.py', ['LeRobotAPI', 'LitServer', 'setup', 'predict']),
    ('model.py', ['LeRobotModel', 'MockPolicy', 'create_model']),
    ('client.py', ['RobotClient', 'predict', 'demo_control_loop'])
]

for filename, expected_items in files_to_validate:
    filepath = os.path.join(endpoint_dir, filename)
    
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                
            # First check if it's valid Python
            compile(content, filepath, 'exec')
            
            # Then check for expected content
            missing_items = [item for item in expected_items if item not in content]
            
            passed = test(f"4.x {filename} has expected components",
                          len(missing_items) == 0,
                          f"Missing: {missing_items}" if missing_items else "")
            tests_passed += passed
            tests_failed += not passed
            
        except SyntaxError as e:
            passed = test(f"4.x {filename} is valid Python", False, str(e))
            tests_failed += 1
    else:
        passed = test(f"4.x {filename} exists", False, "File not found")
        tests_failed += 1

# ========== SECTION 5: Mock Implementation Tests ==========
print("\n5. Mock Implementation Tests:")

# Test 15: Run mock tests with validation
mock_test_path = os.path.join(endpoint_dir, "test_mock_minimal.py")
if os.path.exists(mock_test_path):
    result = subprocess.run(
        ["python3", mock_test_path],
        capture_output=True,
        text=True,
        cwd=endpoint_dir  # Run from the correct directory
    )
    
    # More strict validation - check for specific outputs
    output = result.stdout
    has_robot_test = "Testing SimpleMockRobot" in output
    has_policy_test = "Testing SimpleMockPolicy" in output
    has_control_test = "Testing control loop" in output
    has_success = "All concept tests passed" in output
    
    passed = test("5.1 Mock implementation runs all tests",
                  result.returncode == 0 and all([has_robot_test, has_policy_test, has_control_test, has_success]),
                  f"Exit:{result.returncode}, Robot:{has_robot_test}, Policy:{has_policy_test}, Control:{has_control_test}")
    tests_passed += passed
    tests_failed += not passed
    
    # Test 16: Verify control loop performance claim
    if "Average Hz:" in output:
        hz_line = [line for line in output.split('\n') if "Average Hz:" in line][0]
        try:
            hz_value = float(hz_line.split(':')[1].strip())
            passed = test("5.2 Mock control loop achieves >30Hz",
                          hz_value > 30,
                          f"Got {hz_value}Hz, need >30Hz")
            tests_passed += passed
            tests_failed += not passed
        except:
            test("5.2 Control loop Hz parsing", False, "Could not parse Hz value")
            tests_failed += 1
    else:
        test("5.2 Control loop performance", False, "No Hz output found")
        tests_failed += 1
else:
    test("5.x Mock test file", False, "test_mock_minimal.py not found")
    tests_failed += 2

# ========== SECTION 6: Integration Validation Tests ==========
print("\n6. Integration Validation Tests:")

# Test 17: Verify serve.py properly integrates LeRobot
try:
    serve_file = "solo_server/commands/serve.py"
    with open(serve_file, 'r') as f:
        serve_content = f.read()
    
    # Check for proper integration points
    integration_points = [
        ("LeRobot in ServerType enum", "LEROBOT = \"lerobot\""),
        ("LeRobot config loading", "get_server_config('lerobot')"),
        ("LeRobot default model", "lerobot_config.get('default_model')"),
        ("LeRobot server startup", "start_lerobot_server("),
        ("LeRobot in container names", "container_name =")
    ]
    
    all_integrated = True
    for desc, pattern in integration_points:
        if pattern not in serve_content:
            test(f"6.x {desc}", False, f"Missing: {pattern}")
            all_integrated = False
            tests_failed += 1
    
    if all_integrated:
        test("6.1 All LeRobot integration points present in serve.py", True)
        tests_passed += 1
        
except Exception as e:
    test("6.x serve.py integration", False, str(e))
    tests_failed += 1

# Test 18: Verify server_utils.py has proper hardware support
try:
    utils_file = "solo_server/utils/server_utils.py"
    with open(utils_file, 'r') as f:
        utils_content = f.read()
    
    # Find start_lerobot_server function
    import re
    func_match = re.search(r'def start_lerobot_server\((.*?)\):', utils_content, re.DOTALL)
    if func_match:
        func_start = func_match.start()
        # Find the end of the function (next def or end of file)
        next_def = utils_content.find('\ndef ', func_start + 1)
        func_content = utils_content[func_start:next_def if next_def != -1 else None]
        
        # Check for hardware passthrough
        has_usb = '/dev/ttyUSB0' in func_content
        has_video = '/dev/video0' in func_content
        has_gpu = '--gpus all' in func_content
        has_env_vars = 'MODEL_ID' in func_content and 'PORT' in func_content
        
        passed = test("6.2 start_lerobot_server has hardware passthrough",
                      all([has_usb, has_video, has_gpu, has_env_vars]),
                      f"USB:{has_usb}, Video:{has_video}, GPU:{has_gpu}, Env:{has_env_vars}")
        tests_passed += passed
        tests_failed += not passed
    else:
        test("6.2 start_lerobot_server function", False, "Function not found")
        tests_failed += 1
        
except Exception as e:
    test("6.x server_utils.py", False, str(e))
    tests_failed += 1

# ========== SUMMARY ==========
print("\n" + "="*50)
print(f"Tests Passed: {tests_passed}")
print(f"Tests Failed: {tests_failed}")
print(f"Total Tests: {tests_passed + tests_failed}")

if tests_failed == 0:
    print("\n✅ All integration tests passed!")
    sys.exit(0)
else:
    print(f"\n⚠️  {tests_failed} tests failed")
    sys.exit(1)