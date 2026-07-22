import graphviz

# Create a new graph using graphviz with more detailed steps and connections
dot = graphviz.Digraph(format='png', engine='dot')

# Define the nodes (steps in the workflow)
dot.node('A', '1. Design Data Model\n(Create Tables and Relationships)')
dot.node('B', '2. Generate Unique Course Identifier\n(Ensure each course has a unique ID)')
dot.node('C', '3. Add Helper Functions\n(Password Check, Course Enrollment)')
dot.node('D', '4. Manage User Registration\n(Create User, Assign Roles)')
dot.node('E', '5. Handle Assignments and Submissions\n(Students submit assignments)')
dot.node('F', '6. Manage Exams and Quizzes\n(Add Questions, Assign Grades)')
dot.node('G', '7. Build User Interface\n(Design Student, Teacher, Admin Views)')
dot.node('H', '8. Test System and Fix Bugs\n(Ensure everything works smoothly)')
dot.node('I', '9. Integrate with External Services\n(Email, Notifications, Third-Party APIs)')

# Add edges (connections between the steps)
dot.edge('A', 'B', label='Design Tables with Proper Relationships')
dot.edge('B', 'C', label='Generate Unique Course ID for Each Course')
dot.edge('C', 'D', label='Implement Helper Functions like Password Validation')
dot.edge('D', 'E', label='Handle User Registration and Assign Roles (Student, Teacher)')
dot.edge('E', 'F', label='Manage Assignment Submissions and Grading')
dot.edge('F', 'G', label='Create and Manage Exams/Quizzes')
dot.edge('G', 'H', label='Design User Interfaces for All Roles')
dot.edge('H', 'I', label='Test the System, Identify Bugs, and Integrate Services')
dot.edge('I', 'A', label='Reiterate and Improve')

# Render the workflow diagram as a PNG image
dot.render('detailed_workflow', view=True)
