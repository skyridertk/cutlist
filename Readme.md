# Cutting Stock Optimizer Module - Implementation Guide

This guide provides instructions for implementing the Cutting Stock Optimizer module in Odoo 18.

## Prerequisites

1. Odoo 18 installed and working
2. Administrator access to your Odoo system
3. Required Python dependencies:
   - NumPy
   - Matplotlib
   - PuLP

## Installation Steps

### 1. Install Required Python Dependencies

SSH into your Odoo server and install the required Python packages:

```bash
pip3 install numpy matplotlib pulp
```

### 2. Copy Module Files

Place the module files in the appropriate directory:

```bash
# If using standard Odoo installation
cp -r cutlist /path/to/odoo/addons/

# If using custom addons path
cp -r cutlist /path/to/your/custom/addons/path/
```

### 3. Update Module List in Odoo

Go to:
- Apps > Update Apps List
- Click "Update" button

### 4. Install the Module

Go to:
- Apps
- Search for "Cutting Stock Optimizer" (remove the "Apps" filter if necessary)
- Click "Install" button

## Configuration

After installation, configure the module:

1. **Set Up Panels:**
   - Navigate to Cutting Stock > Configuration > Panels
   - Create panels with dimensions, materials, and grain direction as needed

2. **Set Up Stock Sheets:**
   - Navigate to Cutting Stock > Configuration > Stock Sheets
   - Define your stock sheets with dimensions and materials

3. **Set Up Optimizer Options:**
   - Navigate to Cutting Stock > Configuration > Optimizer Options
   - Create different optimization configurations (kerf thickness, grain direction, etc.)

## Using the Module

### Creating a Cutting Job

1. Navigate to Cutting Stock > Cutting Jobs
2. Click "Create" button
3. Fill in the form:
   - Name: Give your job a name
   - Stock Sheet: Select a stock sheet
   - Optimization Options: Select an optimization configuration
   - Panels: Add panels and their quantities
4. Click "Save"
5. Click "Set Ready"

### Running Optimization

1. Open a cutting job in "Ready" status
2. Click "Run Optimization" button
3. Wait for the optimization to complete
4. Review the results:
   - Sheet usage ratio
   - Waste area
   - Total panels placed
   - Optimization time

### Viewing the Cutting Pattern

1. Open an optimized cutting job
2. Click "Open Cutting Pattern" button
3. The PDF will open in a new browser tab
4. You can download and print this PDF for your cutting operations

## Troubleshooting

### Dependency Issues

If you encounter issues with Python dependencies:

```bash
# Check if the required packages are installed correctly
python3 -c "import numpy, matplotlib, pulp; print('All dependencies installed')"
```

### Module Installation Issues

If the module doesn't appear in the Apps list:

1. Check the module structure matches Odoo's requirements
2. Ensure the module directory has correct permissions
3. Restart the Odoo server after updating the apps list

### Optimization Issues

If optimization fails or produces suboptimal results:

1. Check the dimensions of your panels and stock sheet
2. Ensure your kerf thickness is set correctly
3. Try relaxing constraints (e.g., allowing rotation)
4. For complex layouts, try breaking the job into smaller batches

## Customization

### Integration with Production Orders

You can integrate this module with manufacturing orders by:

1. Creating a custom field on manufacturing orders to link to cutting jobs
2. Adding a button on manufacturing orders to create cutting jobs
3. Using Odoo's automation features to trigger cutting jobs from manufacturing orders

### Custom Reports

To customize the cutting pattern report:

1. Modify the `report/cutting_pattern_report_template.xml` file
2. Add additional information to the report as needed
3. Create custom paper formats if needed

## Support

For questions or support, contact:
- Email: yoursupport@example.com
- Phone: (123) 456-7890